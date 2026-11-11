# DATABASE.md

Engine: **SQLite** for the prototype (single file, easy to reproduce). Schema is written to be Postgres-compatible via SQLAlchemy 2 + Alembic. Enable `PRAGMA foreign_keys=ON` and WAL mode.

## 1. Conventions

- Primary keys: `id` TEXT (UUIDv7 or ULID, generated in app code).
- Timestamps: `created_at` TEXT in ISO-8601 UTC. Injected clock, not `now()` defaults.
- Money: `amount_minor` INTEGER (minor units) + `currency` TEXT (ISO 4217). Never float.
- JSON columns are TEXT holding canonical JSON; validated by Pydantic before write.
- Hashes: lowercase hex SHA-256 in TEXT.
- Tables are snake_case plural. Events and receipts are **append-only** (enforced by triggers, see section 5).

## 2. Entity overview

```
scenarios ─┐
           ├─< runs >── agent_variants
fixtures ──┘     │
                 ├─< observations
                 ├─< product_facts >─< fact_conflicts
                 ├─< rankings
                 ├─< stability_reports
                 ├─< decisions
                 ├─< credentials
                 └─1 receipts >─< receipt_events
benchmark_batches ─< runs
signing_keys
```

## 3. Tables

### scenarios
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | e.g. `S5_spec_swap` |
| title | TEXT | |
| kind | TEXT | `attack` or `benign` |
| attack_type | TEXT NULL | `phishing_store`, `prompt_injection`, ... |
| definition | TEXT | JSON scenario spec |
| expected_outcome | TEXT | what counts as attacker success |
| version | INTEGER | bump on any change |

### fixtures
`id`, `scenario_id` FK, `name`, `content_hash`, `path`, `created_at`. Fixture content lives on disk; only hash + path in DB.

### agent_variants
`id`, `name` (`baseline`, `warrant`), `model_name`, `model_version`, `prompt_version`, `config` (JSON), `config_hash`. Unique on `(name, config_hash)`.

### benchmark_batches
`id`, `created_at`, `git_commit`, `seed`, `notes`. Groups runs so reports are reproducible.

### runs
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| batch_id | TEXT FK | |
| scenario_id | TEXT FK | |
| variant_id | TEXT FK | |
| repetition | INTEGER | 1..N |
| seed | INTEGER | |
| status | TEXT | `completed`, `error`, `timeout` |
| purchased_item | TEXT NULL | |
| attacker_success | INTEGER | 0/1 (attack scenarios) |
| benign_success | INTEGER NULL | 0/1 (benign scenarios) |
| false_block | INTEGER NULL | 0/1 (benign scenarios) |
| latency_ms | INTEGER | |
| llm_cost_micro_usd | INTEGER | |
| started_at / finished_at | TEXT | |

Unique `(batch_id, scenario_id, variant_id, repetition)`.

### observations
`id`, `run_id` FK, `url`, `content_hash`, `byte_size`, `fetched_at`. Raw content stored on disk by hash, not in DB.

### product_facts
`id`, `run_id` FK, `observation_id` FK, `name`, `price_minor`, `currency`, `spec` (JSON), `gtin` NULL, `seller_id`, `source_span` (JSON: start/end offsets).

### fact_conflicts
`id`, `fact_id` FK, `field`, `extracted_value`, `reference_value`, `severity` (`low|medium|high`), `reference_source`.

### rankings
`id`, `run_id` FK, `perturbation` (`none|strip_persuasion|shuffle_<k>`), `ordered_fact_ids` (JSON), `scores` (JSON), `winner_fact_id`.

### stability_reports
`id`, `run_id` FK, `winner_counts` (JSON), `stable` INTEGER, `threshold` REAL, `flips` (JSON).

### decisions
`id`, `run_id` FK UNIQUE, `result` (`ALLOW|STEP_UP|BLOCK`), `reasons` (JSON array of reason codes), `policy_version`, `amount_minor`, `currency`.

### credentials (simulated)
`id`, `run_id` FK, `cart_hash`, `merchant_id`, `amount_minor`, `currency`, `nonce` UNIQUE, `expires_at`, `redeemed_at` NULL, `signature`.

### receipts
`id`, `run_id` FK UNIQUE, `final_hash`, `signature`, `signing_key_id` FK, `created_at`, `export_path`.

### receipt_events (append-only)
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| receipt_id | TEXT FK | |
| seq | INTEGER | 0-based, contiguous |
| type | TEXT | `intent`, `observation`, `facts`, `conflicts`, `ranking`, `stability`, `decision`, `credential`, `settlement` |
| payload | TEXT | canonical JSON |
| payload_hash | TEXT | |
| prev_hash | TEXT | `000...0` for seq 0 |
| event_hash | TEXT | SHA-256 of canonical event |
| created_at | TEXT | |

Unique `(receipt_id, seq)`.

### signing_keys
`id`, `algorithm` (`ed25519`), `public_key`, `created_at`, `revoked_at` NULL. **Private keys are never stored in the DB** (see `SECURITY.md`).

## 4. Indexes

- `runs(batch_id, scenario_id, variant_id)`
- `product_facts(run_id)`, `fact_conflicts(fact_id)`
- `rankings(run_id, perturbation)`
- `receipt_events(receipt_id, seq)` (unique)
- `credentials(nonce)` (unique)

## 5. Integrity rules

- `receipt_events` and `receipts`: triggers block `UPDATE` and `DELETE`.
- `seq` must equal previous `seq + 1`; `prev_hash` must equal previous `event_hash` (checked in app and by a verification query).
- `decisions.result = 'ALLOW'` is required before a `credentials` row can be created (app-level check + test).
- Scenario edits create a new `version`; old runs keep referencing the version they used.

## 6. Key queries (reference)

```sql
-- Attack success rate by scenario and variant
SELECT scenario_id, v.name, AVG(attacker_success) AS asr, COUNT(*) AS n
FROM runs r JOIN agent_variants v ON v.id = r.variant_id
WHERE r.batch_id = :batch AND r.status = 'completed'
GROUP BY scenario_id, v.name;

-- False-block rate on benign scenarios
SELECT v.name, AVG(false_block) AS false_block_rate, COUNT(*) AS n
FROM runs r JOIN agent_variants v ON v.id = r.variant_id
JOIN scenarios s ON s.id = r.scenario_id
WHERE s.kind = 'benign' AND r.batch_id = :batch
GROUP BY v.name;
```

Confidence intervals (Wilson) are computed in Python (`bench/report.py`), not SQL.

## 7. Migrations & seeding

- Alembic; one migration per change; never edit applied migrations.
- `warrant db seed` loads scenarios from `bench/scenarios/*.yaml` and registers fixtures by hash.
- Test DB: in-memory SQLite per test session; no shared state between tests.

## 8. Retention & privacy

- No real personal data is stored. Fixtures use synthetic users and fictional merchants.
- Raw page bytes are stored on disk by content hash and can be purged without breaking receipts (receipts reference hashes).
