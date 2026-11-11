# WARRANT — Final Implementation and Security Audit

## Scope

This audit describes the Stage 4–6 prototype on `priyansh/pipeline-4-6` and its compatibility with the supplied team archives. It is not a production security certification or a claim that the complete shopping workflow is integrated.

Stage 4 provides typed perturbation and stability evaluation, with persistence adapters for Ayush's canonical database. Stage 5 provides deterministic policy evaluation and a same-run evidence assembly boundary. Stage 6 provides cart canonicalization, EdDSA token verification, transactional one-time redemption, and a mock gateway. Public credential issuance remains disabled because the agreed winner-to-cart identity contract is missing.

## Integration status

- **Mayank / Stages 1–3:** The adapter consumes selection and ranking outputs only when the integration supplies authoritative candidate and actual-seller mappings. Mayank's output does not include typed source blocks required to rerun extraction after persuasion stripping, and its fact IDs depend on page content. URL-derived merchant IDs are not treated as seller identity.
- **Ayush / database:** Runtime persistence uses Ayush's `warrant.db` repositories and shared transaction helper. The local raw-SQL ledger is test-only. Migrations 0008 and 0009 and their regression tests are included.
- **Deepika / API:** The supplied archive contains frontend code, not backend routes or request models. The API must assemble policy evidence from trusted stage outputs and persistence reads.
- **Stage 7:** Receipt ownership and event contracts remain unconfirmed; this branch does not add a receipt implementation.

## Stage 4 and Stage 5 behavior

Stage 4 strips only explicitly labeled marketing/review prose, keeps structured fields, hashes transformed typed content, validates callback outputs, and records whether perturbations changed input. Winning product comparisons include seller, SKU, GTIN, price, currency, shipping, additional charges, and specifications. Callbacks receive a cooperative timeout contract; synchronous callbacks are not forcibly terminated.

Stage 5 applies the documented deterministic priority: hard blocks dominate step-up conditions. `evaluate_same_run` checks run ownership, winner and persisted-fact identity, intent constraints, and full stability evidence. It rejects missing, failed, skipped, incomplete, wrong-winner, invalid-threshold, or no-meaningful-shuffle evidence. These Python DTOs are not cryptographic attestations, so the API must construct them from trusted outputs.

## Stage 6 security boundary

The mock gateway verifies EdDSA signature, issuer, audience, token shape and times, expected run ID, cart hash, merchant, amount, and currency before redemption. The canonical database compare-and-set checks the signed authorization fields and consumes the nonce within a transaction.

`issue_credential` deliberately rejects issuance until an authoritative mapping connects the persisted Stage 3 winner and actual seller to cart product identity, quantity, price, and total composition. `create_after_allow` and `store_credential` are persistence APIs; they must not be exposed as authorization or issuance endpoints. `persist_decision` and `SharedCredentialLedger.create_after_allow` both write the run's decision. Calling both for one run causes a duplicate-decision failure. The end-to-end credential flow is incomplete and must not be represented as secure or complete.

Migration 0008 backfills a historical ALLOW winner only from exactly one base ranking; missing or ambiguous proof aborts the migration, and approval hashes are not fabricated. Migration 0009 checks for duplicate credential run IDs before adding uniqueness and does not rewrite or delete rows.

## Verification

Commands run against the current working tree:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider tests/test_integrity.py tests/test_policy.py tests/test_policy_evidence.py tests/test_credentials.py tests/test_mayank_adapter.py tests/db/test_stage46_persistence.py tests/db/test_redemption_concurrency.py
ruff check --no-cache .
ruff format --check --no-cache .
mypy --strict src
git diff --check
```

Results: full pytest **356 passed**; focused Stage 4–6 pytest **173 passed**; Ruff check passed; Ruff format check passed with **100 files formatted**; strict mypy passed with no issues in **62 source files**; `git diff --check` passed. The full suite includes migration-backed tests.

Environment: CPython 3.12.10, SQLAlchemy 2.0.55, Alembic 1.20.1, Pydantic 2.14.1, PyJWT 2.15.1, pytest 9.1.1, Ruff 0.17.2, and mypy 2.4.0. Dependency versions were not changed.

## Remaining limits

No API-to-checkout workflow or production payment integration is implemented. Mayank's missing typed source blocks and actual seller identity prevent full Stage 4 callback integration. The cart-to-winner mapping remains unresolved, so `issue_credential` stays disabled. Passing tests do not remove these interface gaps or certify production security.
