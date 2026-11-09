# Database delivery validation

Branch: `feat/ayush-db`, based on `main` commit `190dde58cba51423e71e7b893d22e4ad94eda599`.

## Local evidence

- Full pytest suite: **171 passed** on Windows/Python 3.12.10.
- Ruff formatting/checks: passed.
- Strict mypy: passed on 42 source files.
- Alembic metadata check: no pending upgrade operations.
- Fresh migration, repeat migration and upgrades from every preceding revision preserve data; final schema has 15 application tables and seven revisions.
- Sample seed creates one scenario/two fixtures; second identical seed creates nothing and reports three unchanged identities.
- Complete hashed locked requirements: `pip-audit --disable-pip --require-hashes --strict` reports no known vulnerabilities. This is a point-in-time dependency check, not proof the application is vulnerability-free.
- Wheel packaging includes the Alembic environment, template and revision files.
- Runtime database, virtual environment, tooling/cache and secrets files are excluded from Git.

## Independent review and corrections

A fresh reviewer inspected the entire branch and independently ran the original 156-test suite. Its important finding was SQLite REPLACE bypassing UPDATE/DELETE guards with recursive triggers disabled. Regression tests reproduced the overwrite before the fix.

The engine now enables recursive triggers on every connection. Additive migration 0007 also rejects colliding INSERT identities before replacement, covering primary keys and alternate unique keys in scenarios/receipts/events. Tests cover recursive triggers both enabled and disabled. Existing applied revisions were left unchanged.

The review also reproduced untyped SQLite WAL-bootstrap failures. These were treated as a public error-boundary issue and corrected: initialization errors retain their cause and become PersistenceError/DatabaseBusyError; an unusable database path exits the CLI with status 1 without a traceback. Both regressions were observed failing before correction; the full 171-test suite passed afterward.

## Decisions and practical limits

- The requested feature branch reuses the initially empty checkout. No teammate code was displaced; no extra worktree was needed.
- Focused commits are delivered through one draft PR because their shared DTO/schema contract must be reviewed together. This produces a larger final diff than individual commits.
- Scenario revisions, required SKU, active-run state, explicit skipped/missing-reference states and input manifests implement the plan's proposed gap resolutions. Team adapters must review those shapes.
- Runtime callers generate UUIDv7/ULID IDs. Seed IDs are deliberately deterministic logical/content identities, so repeat setup does not create random duplicates.
- `store_credential` requires an injected `now` keyword so expiry is checked without hidden clock reads. Callers must pass it.
- Source-span coordinates and bounds belong to the extractor; DB preserves ordered nonnegative offsets. The team must agree which representation those offsets describe.
- Signature/envelope verification, token verification, policy correctness, benchmark labels and statistical meaning remain upstream-owned. The DB does not establish their semantic truth.
- Receipt creation can follow terminal run status; receipt/credential stage markers are explicit orchestration records. Consumers should check actual receipt presence.
- Completed labels need not imply every pipeline stage exists, because baseline runs differ. The benchmark owner must not label incomplete outcomes as successes.
- Multiple ranking records for a perturbation remain permitted until the team agrees a unique perturbation identity. Consumers select the intended record.
- Arbitrary JSON flip/payload semantics remain owner-defined; cross-run references buried inside those objects cannot be inferred by storage code.
- SQL immutability is specifically enforced for scenarios and receipt evidence. Ordinary evidence/fixture/variant mutation boundaries are repository contracts, not a claim to resist a privileged direct SQL writer.
- Let failed writes escape the transaction boundary. Catching errors and committing incomplete work violates the supported pattern.
- Sessions are per request/thread. Reusing one concurrently or caching a long-lived read transaction is unsupported.
- Frozen Pydantic objects do not recursively freeze JSON, and extreme integer/direct-Python argument bounds may need additional API validation. Review found no persisted corruption or false authorization through supported typed usage from those cases.
- PostgreSQL execution, actual security corpus, pipeline, API, frontend and real receipt interoperability are separate team integrations. Their completion is not claimed here.
- Dependency audit is separate from application review and requires the public vulnerability service. Locked package hashes are retained in the exported audit input.

No remaining review findings were deferred as minor polish. Real receipt verifier integration remains explicitly pending, as described in [the contract](database-contract.md).

Remote CI results must be checked on the draft PR; the local Windows results above do not establish Ubuntu/remote execution success.
