# Security and privacy notes

This document distinguishes controls present in the Stage 4–6 code from requirements or controls that belong to unimplemented stages/integration. It describes a research prototype; it is not a security certification or payment-system approval.

## Trust boundaries and threats

| Input/boundary | Trust status | Current handling |
|---|---|---|
| Storefront HTML, text, structured metadata, reviews | Untrusted | Stage 4 receives typed blocks and passes them only to injected extraction code; it executes none of the content. |
| Extraction model output | Untrusted | Stage 4 validates fact types/fields, candidate membership, run IDs, winning seller/SKU identity, and same-candidate purchase-field drift. Full extraction schema validation belongs to Stage 1 and is not implemented here. |
| Independent-source facts and conflict severity | Untrusted evidence | Stage 5 consumes typed conflicts; any `high` conflict blocks. Stage 2's source independence and severity assignment are not proven by Stage 5. |
| Ranking output | Untrusted evidence | Stage 4 checks winner membership and run identity. Stage 5 does not rerank; correctness of the deterministic scorer belongs to Stage 3. |
| API/client requests | Not implemented | Deepika's API layer must validate request shapes, bound payload sizes, apply timeouts, and avoid exposing stack traces. |
| Local SQLite database | Trusted only under the local prototype assumption | Runtime persistence uses Ayush's `warrant.db` repository functions through `SharedCredentialLedger`. Forward-only migrations add decision provenance and one-per-run uniqueness. Migration-backed repository tests passed with pinned dependencies. The old raw-SQL ledger exists only as test support, not as a runtime path. |
| Signing private key and passphrase | Secret | Ed25519 private key is loaded from encrypted PEM; key bytes and passphrase are not included in results or logs by these modules. Filesystem/OS protection remains the operator's responsibility. |
| PayPal | Not connected | No adapter, PayPal credentials, production endpoint, sandbox order, or capture flow exists in this branch. |

Indirect prompt injection remains a risk for extraction. A prompt instruction is a mitigation, not a security boundary. Stage 4's deterministic perturbations measure changes in winner under selected presentation transformations; they do not prove that an extraction is truthful or injection-resistant.

## Validation and deterministic policy

The Stage 4 contracts require candidate identifiers and structured extraction/ranking results. Missing baseline winners, empty/duplicate candidate sets, candidate membership changes, malformed facts, missing/ambiguous winner facts, missing winner SKU identity, commercial-field drift, bad callback run IDs, exceptions, and timeouts prevent a stable report. Exception contents are omitted; safe codes and exception class names do not include source text. Callback timeouts are cooperative: Python does not terminate a synchronous callback that ignores its timeout. The current interface still cannot map Mayank's distinct perturbation fact IDs to parent-run Ayush fact IDs.

Persuasion stripping removes only `marketing` and `review` blocks. Fact, structured, and unclassified content is preserved. The current code does not infer block labels from arbitrary HTML; a mistaken upstream label can remove a fact or leave persuasion in place.

Stage 5 is a pure deterministic function with machine-readable reason codes. Its emitted policy version fingerprints configured thresholds. High-severity conflict, disallowed winner, and hard-constraint violation take `BLOCK` priority over every step-up condition. Unstable winner, qualifying no-reference purchase, upstream error, missing evidence, invalid inputs, missing currency threshold, or missing `winner_fact_id` cannot produce `ALLOW`. An approval hash deterministically covers run, winner fact, result, reasons, policy version, amount/currency, and evaluator evidence. The function contains no LLM or current-time dependency. `evaluate_same_run` validates typed same-run evidence and rejects stability reports with missing, skipped, failed, incomplete, wrong-winner, threshold-invalid, or no changed-shuffle evidence. These DTOs are caller-constructible Python objects, not cryptographic attestations; an API must assemble them from trusted outputs and persistence reads, never from client booleans. MEDIUM conflicts do not independently step up or block; this remains an owner decision.

## Cart hashing and signed credential

The cart model accepts only declared fields: merchant ID, currency, integer amount in minor units, item identity/SKU, positive integer quantity, integer unit price, tax, shipping, and discount. It rejects floats, booleans used as integers, invalid amount totals, malformed currency shape, and unsafe JSON integer magnitudes. Currency validation checks three uppercase letters; it does not validate membership against a full ISO 4217 registry.

Canonical bytes use UTF-8 JSON, sorted ASCII field names, compact separators, no floats, fixed schema version `warrant-cart-v1`, and item sorting on semantic item fields. SHA-256 is computed over these bytes. This is a deliberately constrained project format; it is not a claim of complete RFC 8785/JCS support. Additions to purchase-relevant fields require a cart schema version change and compatibility tests.

Test-fixture credentials use compact JWT/JWS with `alg=EdDSA` (Ed25519), a stable `kid`, and claims for issuer, audience, version, run ID, cart hash, merchant, amount, currency, issue/expiry times, and unique nonce. Verification pins EdDSA, resolves `kid` only from configured public keys, validates issuer/audience and strict claim types, checks expiry/issue time against a constructor-injected clock, then checks cart bindings. The gateway requires the expected run ID and compares it with the signed claim and persisted row. The API request cannot supply the clock. No algorithm is selected from the token without an allow-list.

The public `issue_credential` function remains fail-closed. `Decision` and the migrated decision row carry the exact `winner_fact_id` and deterministic approval hash. However, no approved contract maps that fact to the cart's stable item ID, actual seller, SKU, quantity, unit price, and reconciled shipping/tax/discount total. Equal prices are insufficient. `issue_credential` creates no token or credential row while this mapping is absent. Persistence APIs can store records when repository preconditions are met, but they do not establish winner-to-cart identity. `create_after_allow` and `store_credential` are persistence APIs, not authorization or issuance endpoints, and must not be exposed directly as public routes. The persisted signature field stores only the compact JWS signature segment, not the bearer token.

The signed token carries `run_id` and `approval_hash`; `MockGateway.authorize` requires the expected run ID and validates issuer, audience, signature, expiry, cart hash, merchant, amount, currency and approval-hash shape before database access. The shared adapter calls `redeem_credential` in a fresh `transaction()` and passes signature-verified authorization values to a conditional repository UPDATE as its first database operation. The predicate compares nonce, run ID, signature segment, approval hash, cart hash, merchant, amount, currency, unused state, and expiry. Acceptance is returned only after transaction commit. Exact winner-to-cart binding remains unresolved and `issue_credential` is disabled.

## Nonce replay protection and database integration

Runtime credential persistence uses `SharedCredentialLedger`, which wraps Ayush's `save_decision`, `store_credential`, and `redeem_credential` functions in the shared `transaction()` helper. Decision and credential writes are atomic; a failure rolls back both. Redemption verifies the signed token and submitted cart before opening a fresh transaction, performs the repository's conditional UPDATE as the first database operation, and acts on success only after commit. The UPDATE compares every credential authorization field stored in the row against the signature-verified claim values. Migration `0009_one_credential_per_run` checks for duplicate run IDs before adding a unique constraint; it fails with the IDs and does not delete or rewrite rows. Migration `0008_decision_product_provenance` backfills a legacy ALLOW winner only from exactly one base ranking and fails if that evidence is absent or ambiguous. Legacy approval hashes are not fabricated, so those rows cannot issue credentials. The migration-backed tests passed with the pinned dependencies.

`warrant.policy.persistence.persist_decision` and `SharedCredentialLedger.create_after_allow` each call `save_decision`. Calling both for the same run attempts a duplicate decision insert and fails. Integration must select one decision-writing path. Neither persistence API establishes winner-to-cart identity.

The database owner must configure the documented WAL mode, schema migrations, unique constraints, and filesystem location. The code does not create or migrate the application database. PostgreSQL requires a separate adapter that preserves the same atomic compare-and-set semantics; it is not implemented.

## Ed25519 key handling and rotation

`warrant.credential.keygen` creates an encrypted PKCS#8 private PEM and a public PEM, refuses to overwrite output files, and prompts for the passphrase without echo. On POSIX the private file is created with mode `0600` using exclusive creation, then mode bits are reapplied. On Windows the destination directory's inherited ACL is used; code does not set a per-file NTFS DACL, so operators must restrict that directory. The key loader accepts only Ed25519 keys and returns generic errors. Private keys are never written to SQLite; `.gitignore` excludes key and PEM files.

For rotation, generate a new key pair and new `kid`, configure the signer with the new private key, and add both the new and still-valid old public key to the verifier's `KeyRing`. Retain old public keys until all credentials signed with them have expired or been revoked; then remove them. If a key is compromised, remove its public key immediately and revoke affected credentials in the database. Key distribution and revocation administration are not automated. Back up private keys only through an approved protected channel. The example environment variable is a placeholder; do not commit real values.

On Windows, POSIX mode bits are not a substitute for NTFS ACLs. Operators must restrict access to private key files and the passphrase source. This prototype has no HSM/KMS, secure enclave, or secret manager integration.

## Secrets, logging, and PayPal

- Never commit `.env`, signing private keys, database files, PayPal secrets, or real user/payment data.
- Keep signing passphrases in a protected environment/secret store, not in source, command history, or test reports.
- The Stage 4 report includes exception class/code but not exception message or page body. The core modules do not implement application logging. Integration logging must use run IDs and reason codes, and must not log HTML, reviews, full carts, tokens, private keys, passphrases, or authorization headers.
- API integrations must sanitize client-facing errors, set request/body limits and timeouts, and avoid unsafe retries for nonce redemption.
- PayPal sandbox credentials are not in use. If the team approves the separate sandbox adapter amendment, store sandbox client ID/secret server-side, use only the sandbox base URL, never expose the secret to a browser, and never capture until Warrant authorization is rechecked. Live PayPal credentials/endpoints remain prohibited for this prototype.

## Security tests and remaining limitations

The test suite is intended to cover invalid signatures, expiry, cart/merchant/amount/currency mismatch, replay, concurrent redemption, missing key/database, non-ALLOW issuance, missing evidence, priority ordering, and perturbation failures. Passing local tests demonstrates only those tested paths. It does not prove resistance to a compromised process, hostile database administrator, key theft, side channels, a malicious upstream provider, or production traffic conditions.

The receipt system, API authentication, authorization between users, HTML sanitizer, Stage 1 schema validation, Stage 2 independent-source integrity, benchmark harness, and any PayPal sandbox adapter are not implemented in this branch. A future security review must include the composed application and Ayush's actual migrations, not only these isolated modules.

## Verification status

The current pinned run passed 356 tests, including migration-backed database tests; the focused Stage 4–6 suite passed 173 tests. Ruff check and format check passed, and strict mypy reported no issues in 62 source files. See `docs/FINAL_IMPLEMENTATION_AND_SECURITY_AUDIT.md` for the exact command set and dependency versions.

These tests cover only exercised prototype paths. They do not establish production security or a complete end-to-end credential flow. `issue_credential` remains disabled until exact winner-to-cart identity is defined and verified. `create_after_allow` and `store_credential` are persistence APIs, not authorization endpoints. The receipt system, API authentication, HTML sanitizer, and PayPal adapter are not implemented here.
