# TESTING.md

Two kinds of testing here, and they answer different questions:

1. **Software tests**: does the code do what it says? (unit, property, integration, security)
2. **Evaluation (benchmark)**: does the approach reduce bad purchasing outcomes? (the actual research claim, PRD H1)

A green test suite does **not** show the approach works. Only the benchmark can, and only on its scenarios.

## 1. Test pyramid

| Level | Scope | Tools | Runs |
|---|---|---|---|
| Unit | Pure functions: ranking, policy, hashing, canonical JSON, money math | pytest | every commit |
| Property-based | Invariants over many inputs | hypothesis | every commit |
| Integration | Pipeline end to end with stub/cassette LLM and fixture server | pytest + httpx | every commit |
| Security | Tamper, replay, injection handling, SSRF guard | pytest | every commit |
| Benchmark / eval | Baseline vs Trussted on scenarios, N repetitions | `trussted bench` | on demand + nightly |
| Dashboard | Components, a11y | vitest, Testing Library, axe | every commit (if built) |

Coverage target: >= 90% line and >= 80% branch on `rank/`, `policy/`, `receipt/`, `credential/`, `integrity/`. Coverage is a floor, not a goal.

## 2. Determinism rules

- All LLM calls go through `LLMClient`. Tests use `StubClient` (fixed outputs) or `CassetteClient` (recorded responses). **No live LLM calls in the normal test suite.**
- Time and randomness are injected. Every random operation takes a seeded `random.Random`.
- No network access in tests except the local fixture server on `127.0.0.1`. CI blocks other egress.
- Each test uses its own in-memory SQLite DB.

## 3. Unit tests (examples that must exist)

**rank/**
- Candidate violating a hard constraint is never ranked above one that satisfies it.
- Output is identical regardless of input order (stable tie-break).
- Persuasive text fields are not read (scorer signature takes only structured facts).

**policy/**
- Table-driven test covering every row of the policy table in `ARCHITECTURE.md` 4.5.
- Any raised exception in a stage -> `STEP_UP` (never `ALLOW`).

**receipt/**
- Canonical JSON is identical for key-order-permuted input.
- Changing any byte of any event breaks `verify`.
- Deleting or reordering an event breaks `verify`.
- Wrong public key -> verification fails.

**credential/**
- Expired, wrong-cart, wrong-merchant, wrong-amount, and replayed tokens are all rejected by the mock gateway.

**money**
- `Decimal`/minor-unit arithmetic; no float anywhere (lint rule + test).

## 4. Property-based tests (hypothesis)

- For any list of facts and any permutation of it, `rank` returns the same winner.
- For any receipt built from random valid events, `verify(build(events))` is true; for any single-field mutation, it is false.
- For any random `UserIntent` and facts, policy output is always one of {ALLOW, STEP_UP, BLOCK} and never ALLOW when a high-severity conflict exists.
- `canonical_json(decode(canonical_json(x))) == canonical_json(x)`.

## 5. Integration tests

- Run each scenario fixture through the full pipeline with `CassetteClient`; assert the stored decision, reasons, and that a receipt exists and verifies.
- Fail-closed: inject failures (LLM timeout, schema-invalid output, fixture server 500, missing reference) and assert `STEP_UP`.
- Replay: run the same seed twice; assert identical decision and identical receipt final hash (excluding timestamps, which are injected).

## 6. Security tests

- Fetcher refuses non-allow-listed hosts and cross-host redirects (SSRF guard).
- Extraction output containing path-like or URL-like strings in non-URL fields is rejected.
- Receipt DB triggers: UPDATE/DELETE on `receipt_events` raises.
- Credential nonce reuse is rejected under concurrent redemption (two threads).
- Log capture test: run a full pipeline and assert no private key bytes, no full page HTML, and no card-like numbers appear in logs.
- Dependency audit step (`pip-audit`, `pnpm audit`) in CI.

## 7. Benchmark / evaluation protocol

This section defines how results are produced so they can be trusted.

### Design
- Variants: `baseline` (LLM shopping agent, no layer) and `trussted` (same model + pipeline). Same model, same prompts where applicable, same seeds.
- Scenarios: S1-S7 (attack) and B1-B5 (benign) from `PRD.md`.
- Repetitions: **N >= 30** per scenario x variant for the final report (N >= 10 during development).
- Fixed seeds per repetition; record model name/version, prompt version, git commit, and config hash in `benchmark_batches` / `agent_variants`.
- Because LLM output varies, the baseline and Trussted arms are run **interleaved**, not one after the other, to reduce drift effects.

### Metrics (see PRD section 7)
ASR, false-block rate, benign task success, latency p50/p95, cost per decision, perturbation instability on benign runs.

### Statistics
- Report mean with **95% Wilson interval** for every proportion, and always show `n`.
- Compare arms with a two-proportion test or by CI non-overlap; state which. Do not claim significance from point estimates.
- Report per-scenario results; do not report only an aggregate that hides failures.

### Integrity rules (prevent self-deception)
1. Freeze scenarios, thresholds, and policy config **before** the final run. Tag the commit.
2. Tune thresholds only on a **development** set of scenario variants; report on a held-out set not used for tuning (e.g. different fictional brands, different phrasing, different product categories).
3. Never remove or soften a scenario after seeing results. If a scenario is changed, bump its `version` and rerun both arms.
4. Publish failures. S6 is expected to be undetected, and that must appear in the report.
5. Include at least one **adaptive** variant of S2/S3 (attacker text written after reading the extraction prompt) and report results separately from the fixed set.
6. Record all runs, including errors and timeouts; report the error rate. Do not silently drop errored runs.

### Pass / fail for the research claim
- H1 supported: Trussted ASR CI lies entirely below baseline CI on the primary attack set **and** false-block rate on benign <= 15% **and** latency overhead is reported.
- H1 not supported: any condition above fails. Report it as such.

## 8. Fixtures

- Fictional brands and merchants only. Synthetic products, prices, reviews.
- Each scenario fixture has: HTML pages, a reference-source file (attested feed / catalog), a `UserIntent`, and ground truth (which item is attacker-favoured, which is correct).
- Store fixture content hashes in DB to detect accidental changes.
- Benign fixtures must include legitimate persuasive text (real-looking reviews, sale banners) so false blocks are measurable.

## 9. CI pipeline

1. `ruff format --check`, `ruff check`, `mypy --strict`
2. `pytest -m "not bench"` with coverage gates
3. Secret scan, `pip-audit`, `pnpm audit`
4. Dashboard: lint, typecheck, vitest, axe (if present)
5. Nightly: `trussted bench --n 10` on dev set; upload report artifact; fail if ASR or false-block regresses beyond a set tolerance vs the last tagged run

## 10. Definition of done (per feature)

- [ ] Unit + property tests for new logic
- [ ] Fail-closed behaviour tested
- [ ] No live LLM or network in tests
- [ ] If it affects decisions: scenario(s) updated and benchmark rerun noted
- [ ] Limitations doc updated if a claim or boundary changed
