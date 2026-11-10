# Ayush's Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the TRUSSTED team a reproducible database and typed persistence interface for shopping-agent runs, pipeline evidence, signed receipts, and benchmark results.

**Architecture:** Use synchronous SQLAlchemy 2 repositories over local SQLite, with Alembic owning schema changes. Pipeline and API modules pass validated objects to repositories; they never receive SQLAlchemy rows or write SQL themselves. A caller-owned transaction groups related writes, while final receipt insertion and credential redemption have explicit atomic boundaries.

**Tech Stack:** Python 3.12, SQLAlchemy 2, Alembic, Pydantic v2, SQLite, pytest, Hypothesis, ruff, mypy; uv for environment/lockfile management. Proposed small addition: `rfc8785` for canonical JSON, shared with the receipt owner.

**Spec:** [DATABASE](../../reference/DATABASE.md), [ARCHITECTURE](../../reference/ARCHITECTURE.md), [PRD](../../reference/PRD.md). These are unchanged copies of Ayush's supplied Markdown documents. Additional requirements below come from the supplied kickoff PDF, especially pages 14-21 and 27-30.

**Status:** Implementation plan only. Schema adjustments below are proposals for team review, not previously approved changes. No application code, database, branch, or PR has been created by preparing this plan.

## Global Constraints

- Prototype engine: SQLite; enable `PRAGMA foreign_keys=ON` and WAL for file-backed databases.
- Python 3.12; SQLAlchemy 2; Pydantic v2; schema changes only through Alembic.
- Money: integer minor units plus explicit currency. Never use floating-point money.
- Timestamps: ISO-8601 UTC; obtain time from an injected clock, not database `now()` defaults.
- JSON columns: TEXT containing canonical JSON, validated before writing. Hashes: lowercase SHA-256 hex.
- IDs: application-generated TEXT identifiers; repositories accept IDs explicitly rather than inventing them during reads or retries.
- Receipts and receipt events: append-only; UPDATE and DELETE blocked by database triggers.
- Private signing keys never enter the database. Fixture/page bytes stay on disk; database records contain hashes and metadata.
- Repository functions in `src/warrant/db/` are the only database access used by pipeline/API business logic.
- Retain errors and timeouts. Record seeds, model/prompt/config versions and batch Git commit for reproducibility.
- No live LLM calls or external network in tests. Ordinary tests each get an isolated in-memory SQLite database; WAL, migration and concurrent-writer tests get an isolated temporary file database.
- Pin exact dependency versions in `uv.lock`; select releases at least 14 days old when implementing. Do not infer versions from this plan's date.
- Preserve PostgreSQL portability in column types and repository behavior. SQLite PRAGMAs and trigger DDL belong behind dialect-specific migration/setup helpers. PostgreSQL execution is not a promised deliverable in this prototype.

## Review Focus

1. Historical scenario or fixture changes must not silently change an old run. Covered by Tasks 2-4.
2. Valid individual foreign keys must not allow evidence from different runs to be mixed. Covered by Tasks 5-6.
3. A failed multi-row write must not leave a partial receipt or partial stage result. Covered by Tasks 1, 5 and 7.
4. Two independent database sessions must never redeem the same credential twice. Covered by Task 9.
5. Missing results, skipped checks and failed runs must not become false successes or misleading benchmark denominators. Covered by Tasks 4, 6 and 8.

## Scope and teammate contracts

| Owner | Supplies to Ayush | Ayush supplies |
|---|---|---|
| Mayank, stages 1-3 | Observations, facts, source spans, cross-check outcomes and rankings | Typed save/read functions and same-run integrity checks |
| Priyansh, stages 4-6 | Perturbed rankings, stability, policy decisions and verified simulated-credential data | Storage, ALLOW-before-issuance guard and atomic nonce consumption |
| Deepika, API | Validated use-case inputs and required filters | Session factory and detached, typed read results |
| Receipt owner: currently unassigned | Canonical event definition, completed chain, signature and verifier | Atomic immutable storage, public-key metadata and ordered retrieval |
| Benchmark owner: currently unassigned | Scenario files, ground-truth labels and reporting conventions | Versioned inputs, every run record, counts and raw timing/cost samples |

Ayush does not implement extraction, scoring, decision policy, token/signature cryptography, HTTP routes, the dashboard or confidence-interval calculations in this plan. Creating synthetic seed-loader test files is part of DB work; authoring the benchmark attack corpus is not.

## Proposed decisions to review before their dependent tasks

These resolve gaps in the draft documents. Foundation work can proceed while the relevant owner reviews a later contract.

| Gap | Proposed resolution | Needed before |
|---|---|---|
| Scenario versions are required but not pinned | One immutable `scenarios` row per revision; add `scenario_key` and UNIQUE(`scenario_key`, `version`). Each revision has a distinct `id`; existing scenario FKs pin that revision. | Task 2 |
| Ranking needs SKU | Add explicit `sku` to `product_facts`. Mayank defines mandatory SKU or a deterministic upstream fallback; the DB never guesses identity. | Task 5 |
| No active-run status | Add `running`; terminal statuses remain `completed`, `error`, `timeout`. Add nullable `error_stage`/`error_code`; final fields remain NULL until known. | Task 4 |
| Missing-reference and skipped-check states | Add canonical-JSON `runs.stage_states`. Define states `completed`, `no_reference`, `skipped`, `error`, `timeout`; absent means not yet recorded. Reasons are codes, not raw page text. | Task 4 |
| Receipts cannot be updated to finalize them | Receipt owner collects typed events during execution and supplies a fully signed bundle. Insert the header and all events together in one transaction. No repository operation appends to a finalized receipt. Abrupt process death may leave a running run without a receipt; durable event streaming is extra scope. | Task 7 |
| A run's exact inputs are not otherwise pinned | Persist canonical `intent` plus an `input_manifest` on runs. Manifest entries identify the fixture/reference role, fixture ID and SHA-256 hash. This includes user intent, candidate pages, reference data and ground-truth fixture references. | Task 4 |
| Variant uniqueness can hide model changes | Compute `config_hash` over the full versioned variant envelope: name, model name/version, prompt version and configuration. An existing variant row is immutable. | Task 2 |
| Report denominator is ambiguous | Return eligible outcome counts plus separate error/timeout/running counts. Default eligible outcomes are labeled completed runs of the relevant scenario kind; report owners approve any broader definition. | Task 8 |

Also agree: the source-span offset convention; fact IDs across perturbation extractions; event timestamp mapping (`ts` in the canonical envelope versus `created_at` in storage); and who owns the shared `warrant` CLI entry point. Record decisions in `docs/database-contract.md` during implementation. Do not silently choose another person's product-identity or outcome-labeling rules.

## File map

All implementation paths below are relative to the GitHub repository root, not a nested `warrant/` checkout.

```text
pyproject.toml                         # reuse team scaffold; add DB/runtime and test settings
uv.lock                               # exact resolved dependency versions
.gitignore                            # local DB/WAL/SHM files, .env and content-cache artifacts
alembic.ini                           # migration entry point; URL comes from settings
src/warrant/db/
  __init__.py
  base.py                             # declarative base and named-constraint convention
  session.py                          # settings, engine, sessions and transaction boundary
  values.py                           # UTC, canonical JSON and SHA-256 value adapters
  errors.py                           # typed storage errors; never returns ALLOW
  contracts/
    registry.py                       # scenario, fixture, variant and batch inputs
    runs.py                           # run lifecycle and stage-state inputs/results
    evidence.py                       # observation, fact, conflict and ranking DTOs
    outcomes.py                       # stability and decision DTOs
    receipts.py                       # key, event, finalized bundle and verifier protocol
    queries.py                        # run detail, pages and benchmark count/sample DTOs
    credentials.py                    # simulated credential input; implemented at P1
  tables/
    registry.py                       # scenarios, fixtures, agent_variants, benchmark_batches
    runs.py                           # runs
    evidence.py                       # observations, product_facts, fact_conflicts, rankings
    outcomes.py                       # stability_reports, decisions
    receipts.py                       # signing_keys, receipts, receipt_events
    credentials.py                    # credentials; implemented at P1
  repositories/
    registry.py
    runs.py
    evidence.py
    outcomes.py
    receipts.py
    queries.py
    credentials.py
  seed.py                             # validated YAML load, hash registration, idempotency
  migrations/
    env.py
    script.py.mako
    versions/0001_registry.py
    versions/0002_runs.py
    versions/0003_evidence.py
    versions/0004_outcomes.py
    versions/0005_receipts.py
    versions/0006_credentials.py
src/warrant/cli/db.py                 # register migrate/seed with the team-owned CLI
tests/db/                             # focused tests named in tasks below
tests/fixtures/db/                    # small synthetic loader/integration fixtures
docs/database-contract.md             # payload, ownership and transaction agreement
docs/database-setup.md                # teammate instructions and examples
```

If another branch supplies the scaffold, CLI or shared serialization before execution, extend that code rather than creating competing entry points. No schema creation via `Base.metadata.create_all()` in runtime startup; Alembic is the schema source of truth, including in migration/trigger tests.

## Task 1: Engine, transaction boundary and isolated test harness

**Files:** create `db/base.py`, `db/session.py`, `db/errors.py`, `tests/db/conftest.py`, `tests/db/test_session.py`; add/reuse `pyproject.toml`, `uv.lock` and `.gitignore`.

**Interfaces produced:**
- `DbSettings(url: str, busy_timeout_ms: int = 5000)` (frozen validated DTO).
- `create_db_engine(settings: DbSettings) -> Engine`.
- `create_session_factory(engine: Engine) -> sessionmaker[Session]`.
- `transaction(factory: sessionmaker[Session]) -> AbstractContextManager[Session]`.
- `PersistenceError`, `RecordNotFound`, `DuplicateRecord`, `InvalidTransition`, `InvalidEvidence`, `DatabaseBusyError`.

- [ ] Add failing tests `test_foreign_keys_on_every_connection`, `test_file_database_uses_wal`, `test_transaction_commits`, `test_transaction_rolls_back` and `test_in_memory_database_is_isolated`. Use a temporary test table for transaction checks. Assertions: `foreign_keys == 1`, file `journal_mode == "wal"`, committed row count `== 1`, rolled-back row count `== 0`, and a second isolated database cannot see the first database's rows.
- [ ] Run `uv run pytest tests/db/test_session.py -v`; expect failures because engine/session helpers do not exist yet.
- [ ] Implement the interfaces. Use Python 3.12's non-legacy sqlite3 transaction mode. Set connection PRAGMAs outside active transactions, temporarily adjusting driver autocommit for foreign-key setup. Initialize WAL only for file databases, outside a transaction. A transaction commits once on normal exit and rolls back on error; individual repositories flush but never commit. Give each request/thread its own Session. Follow the [SQLAlchemy SQLite guidance](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) and [SQLite journal-mode limitations](https://www.sqlite.org/pragma.html#pragma_journal_mode).
- [ ] Add parameterized checks for malformed settings and a second pooled connection. In-memory databases are not required to report WAL. Ignore `*.db`, `*.db-wal`, `*.db-shm` and configured local data/cache directories in Git.
- [ ] Run the focused tests, `uv run ruff check src/warrant/db tests/db` and `uv run mypy --strict src/warrant/db`; expect success. Commit as `feat(db): add sqlite engine and transaction boundary`.

## Task 2: Versioned registry schema and validated storage contracts

**Files:** create `db/contracts/registry.py`, `db/values.py`, `db/tables/registry.py`, `db/repositories/registry.py`, `db/migrations/env.py`, `db/migrations/versions/0001_registry.py`, `alembic.ini`, `tests/db/test_registry.py`, `tests/db/test_values.py`, `tests/db/test_migrations.py` and the registry sections of `docs/database-contract.md`.

**Consumes:** Task 1 engine/session functions.

**Interfaces produced:** frozen Pydantic inputs `ScenarioInput`, `FixtureInput`, `VariantInput`, `BatchInput`, with fields matching the corresponding DATABASE table plus proposed scenario changes. Define `canonical_json(value: JsonValue) -> str`, `sha256_hex(data: bytes) -> str` and `utc_text(value: datetime) -> str`. Repositories: `register_scenario(session, value: ScenarioInput) -> str`, `register_fixture(session, value: FixtureInput) -> str`, `register_variant(session, value: VariantInput) -> str`, `create_batch(session, value: BatchInput) -> str`. Every `session` parameter is `Session`; all IDs are `str`.

- [ ] Write failing tests proving: two revisions share a scenario key but have distinct IDs; duplicate key/version and conflicting same-version definitions are rejected; variant identity includes model/prompt/config; missing scenario FKs fail. `assert revision_1.id != revision_2.id`; `assert revision_1.version == 1`; `assert revision_2.version == 2`.
- [ ] Add value tests: `canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})`; hashes are 64 lowercase hex characters; timestamps normalize to a fixed UTC `Z` format with six fractional digits; naive datetimes, non-finite JSON values and malformed hash inputs are rejected. Add a Hypothesis property over finite RFC-8785-compatible JSON values: `canonical_json(json.loads(canonical_json(value))) == canonical_json(value)`. Pydantic money fields added in later tasks use strict nonnegative integers, rejecting floats and booleans.
- [ ] Run `uv run pytest tests/db/test_registry.py tests/db/test_values.py -v`; expect missing schema/functions.
- [ ] Implement the four tables, named constraints and migration 0001. Scenario revisions, fixtures and variant configurations have no update/delete repository methods; reject conflicting re-registration instead of updating history. Add UNIQUE `(scenario_id, name)` for fixture registration and the specified UNIQUE `(name, config_hash)` for variants. Translate named uniqueness/FK violations to the agreed typed storage errors, retaining the original exception cause and leaving rollback to the transaction context. Use the upstream [rfc8785 library](https://github.com/trailofbits/rfc8785.py) after agreeing the shared serializer with the receipt owner; do not claim that sorted keys alone implement all of RFC 8785. Keep columns portable (TEXT, INTEGER/BIGINT and explicit constraints), and use canonical JSON text rather than native JSON operators.
- [ ] Test `alembic upgrade head` against a fresh temporary file, `alembic current`, a repeat upgrade and `PRAGMA foreign_key_check`. Assert exactly four application tables at revision 0001 and the expected named constraints/indexes; the Alembic version table is additional. Add an integrity protection for scenario revision edits in the migration, so accidental SQL cannot rewrite their definitions. Test that protection directly.
- [ ] Run focused tests, ruff and strict mypy; expect success. Commit as `feat(db): add versioned benchmark registry`.

## Task 3: Reproducible scenario and fixture seeding

**Files:** create `db/seed.py`, `src/warrant/cli/db.py`, `tests/db/test_seed.py` and small YAML/content fixtures under `tests/fixtures/db/`; register the command with the existing team-owned CLI.

**Consumes:** Task 2 registration methods and value adapters.

**Interfaces produced:** frozen `SeedSummary(scenarios_created: int, fixtures_created: int, unchanged: int)`; `seed_database(session: Session, *, scenario_dir: Path, fixture_root: Path, now: datetime) -> SeedSummary`. Scenario YAML requires logical key, version, definition, expected outcome and fixture references; finalize its exact shape with the benchmark owner before coding the loader.

- [ ] Write `test_seed_is_idempotent`, `test_new_revision_keeps_old_revision`, `test_same_revision_changed_content_is_rejected`, `test_fixture_hash_mismatch_rolls_back`, `test_fixture_path_cannot_escape_root` and `test_seed_cli`. Assertions: a second seed creates `0` scenarios and `0` fixtures; version 2 leaves version 1 byte-for-byte unchanged; changed input under the same version raises; invalid batches leave no partial registry inserts.
- [ ] Run `uv run pytest tests/db/test_seed.py -v`; expect missing loader/command.
- [ ] Implement validated YAML loading, fixture SHA-256 calculation, root-contained path resolution and all-or-nothing seeding. Store relative paths and content hashes; do not store file bytes in SQLite. Return existing IDs for exact replays. Do not manufacture model configurations or benchmark outcomes in the seeder.
- [ ] Expose `uv run warrant db seed --scenario-dir bench/scenarios --fixture-root bench/storefronts`, reusing the team's CLI mechanism. A small standard-library command adapter is sufficient if no CLI exists; agree ownership before adding `warrant` to project scripts. Keep raw fixture serving/content-store implementation outside this task.
- [ ] Run focused tests. Run the command twice against the small test corpus and assert no duplicates. Production S1/S5/B1 seeding becomes an integration check when the benchmark owner supplies those files. Commit as `feat(db): seed versioned scenarios and fixture hashes`.

## Task 4: Run creation, provenance and terminal transitions

**Files:** create `db/contracts/runs.py`, `db/tables/runs.py`, `db/repositories/runs.py`, migration `0002_runs.py`, `tests/db/test_runs.py`; extend test fixture builders and the contract document.

**Consumes:** registry IDs, session transactions, UTC and JSON adapters.

**Interfaces produced:**
- `RunStart`: ID, batch/scenario/variant IDs, repetition, seed, started_at, canonical intent and input_manifest.
- `RunFinish`: status (`completed|error|timeout`), finished_at, nullable outcome labels, measured latency/cost, purchased_item, error_stage/error_code.
- `StageState`: stage (`extract|cross_check|rank|perturb|decide|credential|receipt`), state (`completed|no_reference|skipped|error|timeout`), optional reason_code.
- `create_run(session: Session, value: RunStart) -> str`.
- `finish_run(session: Session, run_id: str, value: RunFinish) -> None`.
- `record_stage_state(session: Session, run_id: str, value: StageState) -> None`.
- `get_run(session: Session, run_id: str) -> RunRecord` (frozen Pydantic result exposing documented run fields and proposed additions).

- [ ] Add failing tests for creation as `running`, each terminal transition, retained timeout/error records, unique repetition identity, and immutable terminal state. Assert `finished_at is None` initially; `running -> completed` succeeds once; a later terminal overwrite raises `InvalidTransition`.
- [ ] Add historical-provenance assertions: an old run still resolves the original scenario revision and fixture hashes after a new revision is seeded. Reject manifest fixtures belonging to another revision or hashes inconsistent with registered fixtures. Inputs include reference/ground-truth fixtures, not only storefront pages.
- [ ] Run `uv run pytest tests/db/test_runs.py -v`; expect failures before migration/repository implementation.
- [ ] Implement migration 0002 and repositories. Enforce positive repetition, nonnegative measured metrics and consistent finished/started times. Use a conditional update from `running` for finalization. Completed attack runs require an attacker outcome; completed benign runs require benign outcome labels. Failed/unfinished outcomes stay NULL rather than becoming zero. Allow unknown error-run cost/latency to stay NULL. The policy/benchmark owners supply decisions and labels; DB code does not invent them.
- [ ] Keep active transactions short: create the run and commit; call LLM/network stages outside DB transactions; persist each stage in a new transaction. Preserve stage errors without leaking raw exception text. Update terminal result and its metrics together.
- [ ] Run migration and lifecycle tests, ruff and strict mypy; expect success. Commit as `feat(db): persist reproducible run lifecycle`.

## Task 5: Extraction, cross-check and ranking evidence

**Files:** create `db/contracts/evidence.py`, `db/tables/evidence.py`, `db/repositories/evidence.py`, migration `0003_evidence.py`, `tests/db/test_evidence.py`; update contract documentation with Mayank/Priyansh.

**Consumes:** run IDs, agreed SKU/source-span contracts, Task 2 value adapters and caller-owned transactions.

**Interfaces produced:** frozen `ObservationInput`, `ProductFactInput`, `FactConflictInput`, `RankingInput`, mirroring DATABASE fields with explicit SKU. Input datetimes are aware UTC; JSON fields are validated values serialized on write. Functions: `save_observations(session: Session, values: Sequence[ObservationInput]) -> tuple[str, ...]`, `save_product_facts(session: Session, values: Sequence[ProductFactInput]) -> tuple[str, ...]`, `save_fact_conflicts(session: Session, values: Sequence[FactConflictInput]) -> tuple[str, ...]`, `save_ranking(session: Session, value: RankingInput) -> str`.

- [ ] Add failing round-trip tests for observations, source spans, strict integer prices/currency, specifications, conflicts, base rankings and multiple `shuffle_<k>` rankings. Assert retrieved source spans, SKU and candidate ordering equal the supplied values.
- [ ] Add `test_fact_cannot_use_other_runs_observation`, `test_ranking_cannot_include_other_runs_fact`, `test_ranking_winner_must_be_candidate`, `test_duplicate_candidates_rejected`, `test_bulk_save_rolls_back` and invalid source-span tests. A span start must be nonnegative and end greater than/equal to start; its unit/bounds come from Mayank's agreed extraction representation.
- [ ] Run `uv run pytest tests/db/test_evidence.py -v`; expect failures before implementation.
- [ ] Implement migration 0003. Use a composite fact-to-observation FK on `(observation_id, run_id)` backed by UNIQUE `(id, run_id)` on observations. Validate JSON ranking IDs against the same run before insert; a JSON array alone cannot enforce a foreign key. Make a non-NULL winner an actual member of the ordered candidates. Agree representation for no viable candidates (proposed: empty list and NULL winner). Do not recompute rankings or conflicts.
- [ ] Persist each extraction/cross-check/ranking batch atomically using Task 1's transaction boundary. Store raw page hash/size/URL metadata, not HTML. Each perturbation extraction gets its own fact IDs; stable product identity remains upstream seller/SKU data.
- [ ] Run focused tests plus all preceding DB tests and migration tests; expect success. Commit as `feat(db): store extraction and ranking evidence`. Split schema/repository PRs at this boundary if the change would exceed the team's review-size guideline.

## Task 6: Stability reports and policy decisions

**Files:** create `db/contracts/outcomes.py`, `db/tables/outcomes.py`, `db/repositories/outcomes.py`, migration `0004_outcomes.py`, `tests/db/test_outcomes.py`.

**Consumes:** Task 4 run/stage-state types and Task 5 fact/ranking identities.

**Interfaces produced:** frozen `StabilityInput`, `DecisionInput` based on DATABASE fields; `save_stability_report(session: Session, value: StabilityInput) -> str`, `save_decision(session: Session, value: DecisionInput) -> str`.

- [ ] Add failing tests for all three decision values (`ALLOW`, `STEP_UP`, `BLOCK`), reason-code round trips, one decision per run and valid stability data. Assert duplicate decisions raise `DuplicateRecord`, not replacement of the earlier decision.
- [ ] Add tests distinguishing `cross_check/no_reference`, `perturb/skipped` and `perturb/error` from actual completed stability results. Assert a skipped perturbation is not returned as `stable=True`; missing data stays missing. Reject unknown winner identities using the agreed seller/SKU or fact-ID key format.
- [ ] Run `uv run pytest tests/db/test_outcomes.py -v`; expect failures before implementation.
- [ ] Implement migration 0004, result enums/check constraints, strict amount validation and `0 <= threshold <= 1`. Proposed cardinality: one final stability report per run, with all perturbations represented in its counts/flips and rankings. Persist a result and its associated stage-state update together. Priyansh owns policy evaluation and fail-closed behavior; DB errors propagate as typed errors for his boundary handler.
- [ ] Run focused tests and previous DB tests; expect success. Commit as `feat(db): persist stability and policy outcomes`.

## Task 7: Public signing keys and immutable finalized receipts

**Files:** create `db/contracts/receipts.py`, `db/tables/receipts.py`, `db/repositories/receipts.py`, migration `0005_receipts.py`, `tests/db/test_receipts.py` and `tests/db/test_receipt_triggers.py`.

**Consumes:** completed signed bundle and verification callback supplied by the receipt owner. This task's integration depends on that owner being named and agreeing the exact canonical event envelope.

**Interfaces produced:**
- `SigningKeyInput`: documented public-key metadata only.
- `ReceiptEventInput`: documented event fields, including parsed payload plus hashes and aware created_at.
- `FinalizedReceipt`: documented receipt header plus `events: tuple[ReceiptEventInput, ...]`.
- `ReceiptVerifier`: callable protocol `__call__(bundle: FinalizedReceipt) -> None`; failure raises `InvalidEvidence`.
- `register_signing_key(session: Session, value: SigningKeyInput) -> str` and `revoke_signing_key(session: Session, key_id: str, *, revoked_at: datetime) -> None`; revocation preserves public key bytes and old receipts.
- `save_finalized_receipt(session: Session, value: FinalizedReceipt, *, verify: ReceiptVerifier) -> str`.
- `get_receipt(session: Session, receipt_id: str) -> ReceiptDetail`, containing the bundle and public signing-key metadata in sequence order.

- [ ] Add failing tests asserting contiguous sequence `[0, 1, ...]`, first `prev_hash == "0" * 64`, link continuity and `events[-1].event_hash == receipt.final_hash`. Require at least one event. Reject a verifier failure, wrong payload hash, a gap, missing key or second receipt for a run.
- [ ] Add direct-SQL tests for UPDATE and DELETE on both `receipts` and `receipt_events`, including deletion through parent relationships. Each must fail; preserve evidence rather than cascading it away. Add a halfway insertion failure and assert receipt/header/event counts all remain zero after rollback.
- [ ] Run `uv run pytest tests/db/test_receipts.py tests/db/test_receipt_triggers.py -v`; expect failures before implementation.
- [ ] Implement migration 0005, restrictive FKs, UNIQUE `(run_id)` on receipts and `(receipt_id, seq)` on events, indexes and explicit SQLite blocking triggers. Verify the callback before saving. Insert header and events in one caller-owned transaction; expose no per-event append/update/delete operation after finalization. Check payload hashes using the agreed shared canonical serializer. Signature verification and canonical envelope semantics remain the receipt owner's implementation. These triggers enforce the documented UPDATE/DELETE restriction; out-of-band inserts are detected by complete receipt verification rather than presented as impossible.
- [ ] Test migration-installed triggers on a file DB as well as normal repository tests. Alembic autogeneration does not replace review of custom trigger DDL; later table-rebuild migrations must preserve/recreate it. Review the [Alembic batch migration guidance](https://alembic.sqlalchemy.org/en/latest/batch.html) when changing constrained SQLite tables. Retaining revocation metadata must not remove historical verification keys.
- [ ] Run focused tests and prior DB tests. With the real receipt owner's verifier, store/load a signed fixture and verify it offline. Before that integration exists, mark it pending; a test callback is not evidence that cryptographic verification works. Commit as `feat(db): store immutable receipt evidence`.

## Task 8: Typed read interfaces and benchmark data

**Files:** create `db/contracts/queries.py`, `db/repositories/queries.py`, `tests/db/test_queries.py`, `tests/db/test_metrics.py`; extend `docs/database-contract.md`.

**Consumes:** Tasks 2-7. Benchmark owner supplies labels and approves denominator convention. Deepika confirms API filter/pagination needs.

**Interfaces produced:**
- `RunFilter(batch_id: str | None, scenario_id: str | None, variant_id: str | None, status: str | None)`.
- `list_runs(session: Session, filters: RunFilter, *, limit: int = 50, offset: int = 0) -> RunPage`; accept `1 <= limit <= 100`, `offset >= 0`; stable order `(started_at, id)`.
- `get_run_detail(session: Session, run_id: str) -> RunDetail`; includes run, pinned scenario/variant, observations, facts, conflicts, rankings, optional stability/decision and optional receipt reference. Return plain frozen/Pydantic values, not lazy ORM relationships.
- `get_benchmark_counts(session: Session, batch_id: str) -> tuple[BenchmarkCounts, ...]`; group by scenario revision and variant, retaining logical scenario key and scenario kind. Counts: attempted terminal runs, completed, error, timeout, running, attack-eligible/successes, benign-eligible/successes, false-block-eligible/false-blocks.
- `get_benchmark_samples(session: Session, batch_id: str) -> tuple[RunSample, ...]`; include run ID, status, scenario revision/kind, variant ID, nullable latency/cost, perturbation state and nullable stability. Reports can compute p50/p95, costs and instability without losing failed/skipped runs.

- [ ] Add failing query tests for missing IDs, empty batches, filtering, bounded pagination, stable tie ordering and DTO access after the Session closes. Assert an empty eligible denominator returns count `0`, not a fabricated success rate.
- [ ] Add a fixed metrics fixture with completed attack outcomes `[True, False, False]`, one attack error and one attack timeout: assert `attack_eligible == 3`, `attack_successes == 1`, `error == 1`, `timeout == 1`, `attempted == 5`. Add benign false-block outcomes `[True, False]`: assert `false_block_eligible == 2`, `false_blocks == 1`. Add an active run: it increases `running` but not terminal attempted/eligible counts.
- [ ] Run `uv run pytest tests/db/test_queries.py tests/db/test_metrics.py -v`; expect failures before implementation.
- [ ] Implement read repositories and count queries. Never average attack labels over benign records. Do not silently exclude errors from the returned dataset; expose counts explicitly. Wilson intervals and benchmark comparisons remain in `bench/report.py`, outside Ayush's work. Show NULL for unavailable measurements and separate skipped perturbations from unstable ones.
- [ ] Run focused tests and prior DB tests. Give Deepika a typed example and the proposed filters; do not invent HTTP endpoint paths. Commit as `feat(db): expose run and benchmark queries`.

## Task 9: Simulated credentials and atomic single-use redemption (P1)

**Files:** create `db/contracts/credentials.py`, `db/tables/credentials.py`, `db/repositories/credentials.py`, migration `0006_credentials.py`, `tests/db/test_credentials.py` and `tests/db/test_redemption_concurrency.py`.

**Consumes:** Priyansh's validated credential fields, Task 6 decisions and Task 1 transaction/session boundary.

**Interfaces produced:** frozen `CredentialInput` matching DATABASE fields; `store_credential(session: Session, value: CredentialInput) -> str`; `redeem_credential(session: Session, *, nonce: str, now: datetime) -> bool`.

- [ ] Write failing tests that reject issuance for `BLOCK`, `STEP_UP` or missing decisions; duplicate nonces; wrong decision amount/currency; and expired credentials. Valid issuance must refer to an ALLOW decision from the same run. Reject issuance for an error/timeout run. Nonce generation/signing remain Priyansh's responsibility.
- [ ] Add `test_exactly_one_concurrent_redemption_succeeds`: use one temporary file database, two independent sessions and a barrier before the redemption transactions. Assert `sorted(results) == [False, True]` after both workers commit. Add replay and exact-expiry boundary tests: `expires_at == now` is expired. Do not share an ORM Session or an in-memory connection between workers.
- [ ] Run `uv run pytest tests/db/test_credentials.py tests/db/test_redemption_concurrency.py -v`; expect failures before implementation.
- [ ] Implement migration 0006 and unique nonce constraint. Redemption must be one conditional UPDATE with predicates `nonce matches`, `redeemed_at IS NULL`, `expires_at > now`; use [RETURNING](https://www.sqlite.org/lang_returning.html) or a reliable affected-row result to decide whether one row changed. It is the first database operation in its fresh redemption transaction. A prior read followed by an unconditional UPDATE is insufficient.
- [ ] Commit redemption before Priyansh treats the credential as consumed. He verifies token signature, cart, merchant and amount before calling this operation. Distinguish database lock/IO errors from `False` (unknown/expired/already-used); never authorize on a storage error. Use bounded driver lock waiting, not an unbounded retry loop.
- [ ] Run focused tests and all preceding DB tests; expect success. Commit as `feat(db): enforce one-time simulated credentials`.

## Task 10: Fresh-checkout verification and teammate handoff

**Files:** create `tests/db/test_db_handoff.py`, finish `docs/database-setup.md` and `docs/database-contract.md`; add only DB-relevant checks to existing CI, or coordinate a minimal shared CI scaffold with Mayank.

**Consumes:** all preceding tasks; real pipeline/receipt integration requires their owners' implementations. No live model or real payment service is needed.

- [ ] Write a failing DB integration test using typed fixtures: seed a scenario, register a variant/batch, create a run, save observations/facts/conflicts/rankings, store a stability result/decision, finalize a receipt and finish the run. Close the Session; reopen and assert all IDs, scenario revision, reason codes, hashes, event order and metrics are preserved. Use the real receipt verifier when available, otherwise keep that integration explicitly pending.
- [ ] Add a separate error/timeout run, and test that it remains queryable and counted. Inject a failure into a multi-write stage and assert rollback. Test a new scenario revision without changing the old run. For the P1 path, test valid issuance and one-time consumption together.
- [ ] Run migrations on a new temporary file and on each preceding real Alembic revision. Verify data is retained when upgrading and receipt triggers remain active. Do not add artificial product schema changes solely to test a future migration. Never alter an already-applied migration to make a failing upgrade disappear.
- [ ] Document Windows-friendly setup, the DB URL setting, migration/seed commands, transaction examples, typed DTO examples and which teammate supplies each payload. Database URL must come from configuration, with a local untracked `.env` and names-only `.env.example`; no credentials or private keys. Include expected output for an idempotent second seed and error-handling examples for Deepika/Priyansh.
- [ ] Run the verification commands below; record their real results in the PR. Ordinary tests use stubs or local files. A green DB suite alone is not evidence that the security approach reduces attack success.
- [ ] Open small feature PRs from Ayush's branch, request the appropriate teammate's review and use the project's squash-merge convention. No direct push or force-push to `main`. Commit the final handoff as `docs(db): document database integration and validation`.

## Verification commands for execution

These commands are planned interfaces; they do not exist in the currently empty repository until the corresponding tasks supply them.

```powershell
uv sync --locked
uv run alembic upgrade head
uv run alembic current
uv run warrant db seed --scenario-dir bench/scenarios --fixture-root bench/storefronts
uv run warrant db seed --scenario-dir bench/scenarios --fixture-root bench/storefronts
uv run pytest tests/db -v
uv run pytest -m "not bench"
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict src
```

Configure a temporary DB URL for migration/seed smoke checks; do not run them against a teammate's working DB. When the complete application exists, run its required full checks as well. Coverage gates on ranking/policy/receipt/credential/integrity modules belong to the relevant owners; Ayush must not claim to satisfy them by testing repository mocks.

## Suggested PR sequence and exit criteria

| PR | Tasks | Demonstrable result |
|---|---|---|
| 1: DB foundation and registry | 1-2 | Working sessions, migration and immutable scenario/config registration |
| 2: Seeds and run lifecycle | 3-4 | Repeatable seeds and historical, queryable run records including errors |
| 3: Pipeline evidence | 5 | Mayank can persist observations, facts, conflicts and rankings |
| 4: Pipeline outcomes | 6 | Priyansh can persist stability and decisions |
| 5: Receipt storage | 7 | Finalized receipts saved atomically; database mutation tests pass |
| 6: Read/report handoff | 8 | Deepika and benchmark owner can retrieve typed results and counts |
| 7: Simulated credential storage | 9 (P1) | ALLOW guard and two-session single-use test pass |
| 8: Final integration and guide | 10 | Fresh-checkout workflow and team handoff verified |

These are review boundaries, not promised durations. Split a PR further when it exceeds roughly 400 changed lines; prefer additive migrations and independently passing tests. Synchronous engine/schema tasks are dependencies; do not implement later repositories in parallel against incompatible DTOs.

## Definition of Ayush's work being complete

- A fresh checkout can install locked dependencies, migrate and seed without manual SQL.
- All 15 specified application tables exist after the P1 credential task, with the documented constraints and reviewed schema changes.
- Pipeline/API callers use typed repository interfaces and short, explicit transactions.
- Every run retains its exact scenario revision, input references, model/config/prompt metadata and available outcome/error evidence.
- Cross-run references, duplicate benchmark identities, partial writes, receipt mutations and concurrent nonce reuse are rejected by the appropriate tests.
- Deepika can retrieve a complete run without an open ORM Session; the benchmark owner can access both eligible outcomes and error/timeout counts.
- Receipt storage works with the assigned receipt owner's actual verifier. Signing and offline verification are not silently reassigned to Ayush.
- Setup, contract and PR validation notes are delivered. Unfinished external integrations are named rather than reported as completed.

## Sources and technical references

- Supplied [DATABASE](../../reference/DATABASE.md), [ARCHITECTURE](../../reference/ARCHITECTURE.md) and [PRD](../../reference/PRD.md), copied unchanged on 2026-11-09.
- Supplied `C:/Users/Ayush Paul/Downloads/kickoff_document (1).pdf`: DB/schema pp.14-19, module boundaries pp.20-21, database/security tests pp.27-30. These additional requirements are reproduced above so execution does not depend on remembering a chat summary.
- [Current repository](https://github.com/Mayank2177/TRUSSTED/tree/main), checked 2026-11-09: README and LICENSE only. Recheck before implementation to avoid duplicating teammates' new work.
- [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html): transaction control and foreign-key connection configuration.
- [SQLite PRAGMAs](https://www.sqlite.org/pragma.html): WAL initialization and in-memory journal-mode limitations.
- [Alembic SQLite batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html): table rebuild and constraint considerations.
- [SQLite RETURNING](https://www.sqlite.org/lang_returning.html): conditional update result handling.
- [rfc8785.py upstream documentation](https://github.com/trailofbits/rfc8785.py): proposed canonical JSON dependency; verify/pin a suitable release during implementation.
