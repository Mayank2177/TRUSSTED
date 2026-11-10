# SECURITY.md

Two security topics apply here: (A) the security of **this codebase**, and (B) the **threat model the prototype is built to test**. Keep them separate. Read `ARCHITECTURE.md` first.

## 1. Ground rules

1. **No real money, ever.** The prototype uses a mock gateway and synthetic merchants. Never add real card numbers, real payment API keys, or real wallets, even for "quick tests".
2. **No real-brand impersonation.** Phishing fixtures use fictional brands (e.g. "ShopMart"). Do not clone real storefronts, host them publicly, or reuse real logos.
3. **Fixtures stay local.** Attack fixtures (fake stores, injected text) are served on `127.0.0.1` only and are not deployed.
4. **Fail closed.** Any error in a stage yields `STEP_UP` or `BLOCK`, never `ALLOW`.
5. **Treat all external content as untrusted data**: page HTML, reviews, metadata, tool descriptions, extraction-LLM output.

## 2. Assets

| Asset | Why it matters |
|---|---|
| Signing private key (receipts, credentials) | Forged receipts/tokens if stolen |
| Benchmark integrity (scenarios, metrics, seeds) | Results are only credible if not quietly altered |
| LLM provider API keys | Cost and abuse |
| Receipt/event log | Tamper evidence is the point of the log |

## 3. Threat model: the prototype itself

| ID | Threat | Mitigation |
|---|---|---|
| T1 | Prompt injection in page content steers the extraction LLM | Delimited data block, schema-constrained output, no tools exposed to the extraction call, cross-check + perturbation stages, scenario S2/S3 measure it |
| T2 | Extraction output used to build paths/URLs/SQL | Validate and allow-list; never pass LLM output to shell, SQL, or filesystem APIs |
| T3 | Forged or replayed credential | Ed25519 signature, expiry, single-use nonce stored in DB, cart-hash match checked by the gateway |
| T4 | Tampered receipt | Hash chain + signature; `trussted verify` recomputes offline; DB triggers block UPDATE/DELETE |
| T5 | Private key leakage | Key loaded from env/secret file at runtime, never committed, never logged, never in DB; `.gitignore` + secret scanning in CI |
| T6 | Malicious or typosquatted dependency | Pinned lockfiles, avoid releases newer than 14 days, `pip-audit` / `pnpm audit`, review new deps in PRs |
| T7 | SSRF/arbitrary fetch via fixture URLs | Fetcher only allows `127.0.0.1` fixture host + allow-listed paths; block redirects to other hosts |
| T8 | Log leakage of sensitive data | Log hashes not raw HTML; redact keys and tokens; no card-like patterns in fixtures |
| T9 | Quiet metric tuning (insider/self-deception) | Scenario/metric/threshold changes require explicit PR note; scenario `version` bump; batch records git commit + seed |
| T10 | Dashboard XSS from rendered page content | Never render fixture HTML as HTML; show as escaped text/code; CSP header; React default escaping |
| T11 | Unbounded LLM cost / DoS | Per-run token and time budgets, global batch budget, timeouts |

## 4. Threat model: attacks the prototype targets (benchmark scenarios)

| Scenario | Attack | What a pass would mean | Expected limitation |
|---|---|---|---|
| S1 | Look-alike fictional store, lower price | Merchant not in allow-list or no reference -> STEP_UP/BLOCK | Depends on reference data existing |
| S2 | Instruction text injected in listing | Selection unchanged / flagged | Extraction LLM may still be influenced |
| S3 | Persuasive metadata, urgency | Ranking ignores persuasion; stable under strip | Real reviews also stripped |
| S4 | Attacker responds first | Winner stable under shuffle | Position-only attacks only |
| S5 | Spec swap (prose vs structured) | `FactConflict` high -> BLOCK | Needs a second source |
| S6 | Both sources falsified consistently | **Expected to pass undetected** | Documented limitation |
| S7 | Tool description mutates mid-session | Hash-pin mismatch aborts | Only if manifest is pinned at start |

Never claim coverage beyond what these scenarios measure.

## 5. Cryptography rules

- Signatures: **Ed25519** via the `cryptography` library. No custom crypto.
- Hashing: SHA-256. Canonical JSON (RFC 8785-style) before hashing; sort keys, no insignificant whitespace, UTF-8.
- Nonces: 128-bit random from `secrets`, stored for single-use enforcement.
- Key management (prototype): key file path from `TRUSSTED_SIGNING_KEY_PATH`, file mode `0600`. Rotate by creating a new `signing_keys` row; old public keys retained so old receipts stay verifiable. Production would use a KMS/HSM; not in scope.
- Compare MACs/hashes with `hmac.compare_digest`.

## 6. Secrets & configuration

- Secrets only via environment variables or untracked files. `.env.example` lists names, never values.
- CI uses secret scanning (e.g. gitleaks) and blocks merges on findings.
- LLM keys: least privilege, spend-capped at the provider where possible.

## 7. Secure development checklist (per PR)

- [ ] No secrets, keys, or real card-like data added
- [ ] Inputs from LLM/pages validated at the boundary
- [ ] New dependency justified and pinned
- [ ] Errors fail closed with a reason code
- [ ] Logs reviewed for sensitive data
- [ ] Any change to scenarios/metrics/thresholds called out in the description
- [ ] Limitations doc updated if behaviour or claims changed

## 8. Responsible use & disclosure

- The attack fixtures are for testing your own system. Do not point them at third-party sites or services.
- If you discover a vulnerability in a third-party product while researching, disclose it privately to the vendor before publishing details.
- If you find a vulnerability in this project, report it to the maintainer privately (add a contact email here before publishing the repo).

## 9. Out of scope (do not claim)

- Protection of real payment flows, PCI compliance, fraud-network integration.
- Resistance to a determined adaptive attacker. Benchmarks use fixed scenarios; adaptive attacks need separate evaluation.
- Issuer or card-network acceptance of receipts as evidence.
