# Database integration contract

This document records implementation decisions proposed in Ayush's plan. Teammates should review their adapters before merge. Code definitions in `src/warrant/db/contracts/` are the precise types; this guide explains ownership and transaction semantics.

## Ownership and storage conventions

| Owner | Input | Persistence module |
|---|---|---|
| Benchmark/orchestration | Scenario revisions, fixtures, variants, batch, user intent and manifest | `repositories.registry`, `repositories.runs`, `seed` |
| Mayank | Observations, facts with SKU/source span, conflicts, base ranking | `repositories.evidence` |
| Priyansh | Perturbed rankings, final stability, decision, verified token fields | `repositories.evidence`, `repositories.outcomes`, `repositories.credentials` |
| Receipt owner, not yet assigned | Fully signed event chain plus real verifier callback | `repositories.receipts` |
| Deepika/report owner | Filters and reads | `repositories.queries`, `repositories.receipts` |

Cross-module values are frozen Pydantic DTOs with unknown fields rejected. IDs are nonempty application-supplied text, hashes are 64 lowercase SHA-256 hex characters, money is strict nonnegative integer minor units, currencies use three uppercase letters and timestamps must have a timezone. Timestamps are stored in UTC with six fractional digits and `Z`. The currency format check does not validate every ISO registry entry. JSON uses the shared RFC 8785 serializer; inputs outside that canonical format's numeric domain are rejected.

Normal runtime callers generate their UUIDv7/ULID identifiers. The seed loader intentionally uses reproducible logical IDs (`scenario_key@version`) and content-derived fixture IDs, matching the specification's logical scenario-ID examples. It never generates new identities on an identical seed replay.

## Registry and run lifecycle

- `scenarios` holds one immutable row per `(scenario_key, version)`. Its `id` identifies the exact revision. SQL triggers reject scenario UPDATE/DELETE.
- Fixture identities/hashes and agent configurations are registration-only through repositories. The variant hash covers `{name, model_name, model_version, prompt_version, config}`; changing the model or prompt requires a new variant.
- `RunStart` requires batch/scenario/variant IDs, repetition, seed, started_at, intent and input_manifest. Each manifest item is `{role: candidate|reference|ground_truth, fixture_id, content_hash}`. Referenced fixtures must belong to that exact scenario revision and match their recorded hash.
- `create_run` starts `running`. `finish_run` atomically transitions once to `completed|error|timeout`. A terminal run is never overwritten to retry it; choose a new repetition/batch identity according to the benchmark protocol.
- Completed attack runs have an attacker-success label; completed benign runs have benign-success and false-block labels. Unavailable error/timeout outcomes and measurements remain NULL. Finish timestamps cannot precede start timestamps.
- Run identity is unique on `(batch_id, scenario_id, variant_id, repetition)`.

`StageState(stage, state, reason_code=None)` records explicit stage outcomes. Stage names are `extract`, `cross_check`, `rank`, `perturb`, `decide`, `credential`, `receipt`. States are `completed`, `no_reference`, `skipped`, `error`, `timeout`; `no_reference` applies only to cross-checking. Absent means not recorded yet. An identical replay is allowed; replacing a different recorded stage state is rejected.

## Stage evidence

| Input / method | Important shape or behavior |
|---|---|
| `ObservationInput` / `save_observations` | ID, run ID, URL, content_hash, byte_size and fetched_at; no HTML bytes |
| `ProductFactInput` / `save_product_facts` | Source fields plus required SKU; `source_span={start,end}`, `spec` JSON object; `gtin` optional |
| `FactConflictInput` / `save_fact_conflicts` | Parent fact ID; extracted/reference values are JSON values; severity low/medium/high |
| `RankingInput` / `save_ranking` | perturbation `none|strip_persuasion|shuffle_<integer>`; ordered unique fact IDs, finite score map keyed by candidate fact IDs, optional winner from those candidates |
| `StabilityInput` / `save_stability_report` | One per run; winner_counts map of this run's fact IDs to counts; strict boolean stable; threshold 0..1; structured flips |
| `DecisionInput` / `save_decision` | One per run; ALLOW/STEP_UP/BLOCK, reason-code tuple, policy_version, amount_minor and currency |

Fact-to-observation associations use a same-run composite FK. Ranking/stability candidate IDs are checked against their owning run. New evidence/outcomes are rejected for terminal runs.

The extractor owns source-span units and which sanitized/raw representation they reference. DB validation preserves them and checks nonnegative ordered offsets; it does not claim to verify page-content bounds. Each perturbation extraction uses distinct fact IDs; upstream code maps equivalent products using seller/SKU and maps stability counts to the agreed run fact IDs.

Saving nonempty fact/conflict batches records extraction/cross-check completion; a base ranking records rank completion; final stability/decision records perturb/decide completion. Result and stage state share a transaction. Observation fetches alone do not mean extraction completed. Perturbed rankings alone do not mean the full stability check completed.

An empty bulk list has no run ID and records no stage state. The caller explicitly records `cross_check/completed` for no conflicts, `cross_check/no_reference` for a missing source, or `perturb/skipped` for a deliberately skipped check. Missing or skipped data is not stable=True.

## Receipts and keys

`register_signing_key` stores algorithm `ed25519`, public key and creation/revocation timestamps. Private-key fields are not accepted. `revoke_signing_key(..., revoked_at=...)` retains public bytes so historical receipts remain readable.

`FinalizedReceipt` contains receipt header fields and an ordered tuple of `ReceiptEventInput` objects. `save_finalized_receipt(session, value, *, verify: ReceiptVerifier)`:

1. Checks nonempty contiguous sequence beginning at zero, initial previous-hash of 64 zeroes, linked event hashes, canonical payload hashes and matching final hash.
2. Calls the required external verifier for event-envelope hashes and the Ed25519 signature. It must raise `InvalidEvidence` on rejection. There is no production fallback verifier.
3. Checks the public key exists and was valid at receipt creation.
4. Flushes the header/events together inside the caller's transaction. A failure must propagate out so rollback removes partial writes.

Receipt/event UPDATE and DELETE are blocked by SQLite triggers. Connection setup enables recursive triggers, and migration 0007 also rejects INSERT identity collisions before SQLite REPLACE can delete immutable scenario/receipt/event rows, including alternate unique-key collisions. These insert guards remain active with recursive triggers disabled. Restrictive FKs preserve audit evidence on parent deletion. No repository method appends events after finalization. An out-of-band new noncolliding INSERT is not claimed impossible; full receipt verification detects an unexpected event or wrong final chain.

The receipt owner buffers stage events and supplies the final signed bundle. Abrupt process death may leave a `running` record without a finalized receipt. Durable streaming/recovery is not implemented. The owner must agree canonical event-envelope fields and timestamp mapping (`ts` versus stored `created_at`). That integration remains pending and is not simulated as a verified production path.

`get_receipt` returns `ReceiptDetail(bundle, signing_key)` detached from the Session. No `export_path` write is performed by the DB; the receipt owner handles JSON export.

## Simulated credentials

`store_credential(session, value: CredentialInput, *, now: datetime)` deliberately requires an injected current time. It checks a same-run ALLOW decision, matching amount/currency, a nonfailed run and expiry after now. Fresh inputs require `redeemed_at=None`; nonces are unique.

Priyansh verifies token signature, cart, merchant and amount before calling `redeem_credential(session, *, nonce, now)`. Use a **fresh transaction** with redemption as its first DB operation, then commit before treating True as consumed. It uses one conditional UPDATE for unredeemed, unexpired nonce state. Exactly one competing transaction can succeed. `expires_at == now` is expired.

False means unknown/expired/already used. Lock or IO failures raise typed errors; they are not mistaken for authorization. Nonce generation and token signing are upstream responsibilities.

## Read/report interfaces

- `list_runs(session, RunFilter(...), *, limit=50, offset=0)` allows limit 1..100, nonnegative offset and stable `(started_at,id)` ordering. Filters select exact scenario revisions, not all versions of a logical scenario key.
- `get_run_detail` returns run, pinned scenario/variant, observations, product facts, conflicts, rankings, optional stability/decision and optional receipt ID.
- `get_benchmark_counts` groups by exact scenario revision and variant. Completed eligible labels supply attack/benign/false-block numerators and denominators. Error, timeout and active counts remain separate. Terminal attempted count includes completed/error/timeout; it excludes running rows.
- `get_benchmark_samples` retains status, nullable latency/cost, explicit perturbation state and nullable stability for every run in a batch.

The report owner computes confidence intervals, percentiles and statistical comparisons and reviews denominator conventions. No outcome is relabeled by DB code to make metrics look better.

## Errors and transactions

`transaction(factory)` commits only on success, rolls back on any exception and closes the Session. Repository methods flush without commit. Related stage writes belong in that one boundary. Do not catch a failed flush and continue using its Session; exit and roll back first.

Public storage exceptions include `RecordNotFound`, `DuplicateRecord`, `InvalidTransition`, `InvalidEvidence`, `DatabaseBusyError` and `PersistenceError`. Original SQL causes are retained for developers. API/pipeline owners choose safe response/reason codes and avoid exposing raw SQL or external content in logs. Sessions are not thread-safe.
