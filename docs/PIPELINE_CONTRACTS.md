# Stage 4–6 integration contracts

These contracts bridge the current Stage 4–6 modules to the Stage 1–3 work owned by Mayank, Ayush's database work, and Deepika's API orchestration. They do not implement or replace those components. Python types live under `src/warrant/integrity`, `src/warrant/policy`, and `src/warrant/credential`.

## Stage 1–3 to Stage 4

### Intent

`UserIntent` contains:

- `max_price_minor: int | None` — a hard budget in integer minor units.
- `currency: str` — uppercase three-letter currency code.
- `required_specs: Mapping[str, str]` — explicit hard specification requirements.
- `allowed_merchants: tuple[str, ...] | None` — absent means no merchant allow-list; present means only listed sellers.
- `weights: Mapping[str, int]` — deterministic Stage 3 soft-ranking weights.

This is an adapter view of the PRD's hard constraints and soft weights. Mayank may keep a richer canonical model, but the adapter must preserve these meanings and never convert money to floating point.

### Candidate observations

Stage 4 accepts an ordered tuple of `CandidateObservation` with a `candidate_id`, `observation_id`, `source_uri`, source SHA-256, and ordered blocks. Each `ObservationBlock` has a `ContentKind`, original text, and optional structured scalar fields. Kinds are `fact`, `structured`, `marketing`, `review`, and `unclassified`. `candidate_id` is an adapter identifier, not an Ayush database fact ID or proof of stable product identity.

Only `marketing` and `review` prose is removed in the strip-persuasion run. Stage 1's adapter must mark a block as promotional only when the block is actually promotional; facts embedded in mixed prose should be split into factual and promotional segments before this boundary. If a removed prose block also carries structured fields, Stage 4 preserves those fields in a separate `structured` block while dropping its prose. Fact, structured, and unclassified content is retained. Stage 4 does not run a classifier or mutate original input objects.

Every `content_hash` is lowercase SHA-256 of typed blocks serialized as compact UTF-8 JSON in the `warrant-observation-content-v1` format, baseline and transformed alike. The JSON object contains `schema` with that exact version string and `blocks`, an array in source order. Each entry contains `kind`, `text`, and `structured_data` (mapping or JSON `null`). Object keys are sorted lexicographically, Unicode is emitted directly as UTF-8, separators are `,` and `:`, and non-finite/unsupported values are rejected by the typed contract. Candidate ID, observation ID, source URI, and prior hash are excluded. The original upstream hash is retained separately as `source_content_hash`; it is not used as a transformed-content cache key.

Any Stage 1–3 cache for extraction must include both stable product/candidate identity and the Stage 4 typed-content `content_hash` (or key directly on both values). A cache keyed only by `candidate_id` can return extraction for pre-stripped or otherwise stale content. No extraction cache is implemented in this repository, so upstream cache behavior remains unverified.

### Extraction and ranking callbacks

`Extractor.extract(observations, intent, *, run_id, timeout_seconds)` returns `ExtractionResult(run_id, candidate_ids, facts)`. Candidate IDs must be unique and membership-equal to the input set; ordering may reflect transformed input order. Facts are runtime-validated for type, candidate membership, currency, nonnegative integer price/charges, seller, optional SKU/GTIN, and source-span shape. A report can be stable only when the baseline winner has exactly one fact with seller/SKU identity. For a same-candidate winner, seller, SKU, GTIN, price, currency, shipping, additional charges, and specifications are compared across reruns; drift fails that outcome closed. Missing SKU does not fall back to GTIN.

`Ranker.rank(extraction, intent, *, run_id, timeout_seconds)` returns `RankingResult(run_id, winner_candidate_id, ranked_candidate_ids)`. The winner must be non-null and present in the ordered candidate ID list, and ranked candidate IDs must be unique. The existing Stage 3 implementation owns score calculation, hard-constraint filtering, and deterministic tie-breaking; Stage 4 only consumes IDs and does not constrain its score representation.

Each perturbation has a fresh nonempty run ID that must be unique and distinct from the parent run. Callbacks receive but must cooperatively honor the timeout and raise `TimeoutError` when exceeded. Stage 4 does not terminate a synchronous callback that ignores the timeout. Other exceptions are recorded by safe code/type without exception text. A wrong run ID, missing/extra candidate, malformed fact, missing winner fact, duplicate rank ID, or winner outside the candidate set invalidates that perturbation.

### Stability result

`StabilityRunner.evaluate` receives the baseline `run_id`, typed intent, original ordered observations, optional baseline extraction and ranking, and a `StabilityConfig`. Pass `None` when a baseline stage failed; Stage 4 returns a failed report and does not run perturbations. For an intentional cost-control skip, call `StabilityRunner.skipped(run_id=..., reason=...)`; this returns `state=skipped`, `stable=False`, zero planned/failed counts, and no fabricated outcomes. It is distinct from a failed baseline report. Default plan is one strip-persuasion run and five shuffles with seeds `seed + 0` through `seed + 4`. Identity shuffle permutations are redrawn from that shuffle's seeded random stream until the order changes; for a one-candidate input, a shuffle cannot change the input and is reported unchanged. `PerturbationOutcome.changed_input` compares the actual transformed observation tuple with its original tuple. `StabilityReport.changed_count` and `shuffle_changed_count` count actual changed inputs among executed outcomes, including outcomes whose upstream callback later fails. No-op transformations do not increment the counts. The report records explicit state, baseline winner, perturbation winner counts, successful/failed/planned counts, changed counts, flips, errors, and strict threshold `1.0`.

The engine's `stable` value is true only when the baseline winner exists, every planned run succeeds with valid evidence, and each perturbed winner equals the baseline. The configured threshold is fixed at `1.0` by `StabilityConfig`; no configurable partial-stability policy exists. The Stage 5 evidence builder independently checks the report's full outcome list and requires at least one shuffle outcome whose input order actually changed. Therefore a one-candidate Stage 4 report may be internally stable, but cannot by itself authorize Stage 5 ALLOW. Partial, skipped, failed, empty, or incomplete reports do not count as stable evidence. No majority voting is used.

## Stage 2–4 to Stage 5

`PolicyInput` requires the run ID, winning candidate ID, winner permission (`True` only if allowed by the explicit merchant constraint), hard-constraint result, stability result, explicit `no_reference` boolean, amount minor units, and currency. It accepts typed `FactConflict(field, severity, fact_id)` and upstream failure records. Missing evidence uses `None`; it is not interpreted as success.

`PolicyConfig` requires an explicit policy-family version and a mapping of currency to no-reference step-up thresholds in minor units. The emitted decision version appends a deterministic fingerprint of the sorted threshold configuration, so a threshold change changes the persisted policy version. No default threshold is invented. A missing threshold when the no-reference rule applies produces `STEP_UP`.

Decision priority is: high-severity conflict `BLOCK`; unpermitted winner or hard-constraint violation `BLOCK`; unstable winner `STEP_UP`; no reference and amount greater than/equal to configured threshold `STEP_UP`; upstream error/timeout `STEP_UP`; otherwise `ALLOW`. Block conditions dominate step-up conditions. Missing or malformed safety evidence, including a missing distinct `winner_fact_id`, produces `STEP_UP`. `Decision` includes run ID, outcome, ordered machine-readable reason codes, policy version, amount, currency, exact winner fact ID, and deterministic `approval_hash`.

`evaluate_same_run` in `warrant.policy.evidence` is the typed Stage 5 assembly boundary. It derives permission and hard-constraint results from the validated intent and unique winner fact, checks Stage 1–4 run IDs and winner membership, requires an explicit candidate-to-persisted-fact mapping, and accepts stability only when the full Stage 4 report is complete, successful, strict-100%, winner-consistent, and contains at least one changed shuffle. Missing reference evidence becomes unknown and cannot allow. This DTO builder is not a cryptographic attestation; application code must assemble its input from trusted stage outputs and persistence reads, never directly from client-supplied flags. `PolicyInput` remains constructible for unit tests and the pure evaluator. `persist_decision` stores a decision through Ayush's repository with same-run winner validation. Medium-conflict policy remains as documented in the policy requirements; no separate owner-policy engine is invoked by this function.

## Stage 5–6

`Cart` includes merchant ID, integer `amount_minor`, uppercase currency, item tuple, tax, shipping, and discount. Each `CartLine` includes product ID, optional SKU, positive quantity, and unit price in minor units. The total must equal line subtotals + tax + shipping − discount. Current v1 cart canonicalization includes every declared field, normalizes identifiers to Unicode NFC, sorts lines by identity/quantity/price, emits compact UTF-8 JSON with fixed schema marker `warrant-cart-v1`, and SHA-256 hashes those bytes.

`issue_credential` checks the `Decision` and cart amount/currency, then currently denies every call because exact winner-to-cart identity is not proven. This statement is scoped to that issuance function. `create_after_allow` and `store_credential` are persistence APIs, not authorization or issuance endpoints; they must not be exposed directly as public routes. They persist records if their repository conditions are met, but do not prove the submitted cart contains the authorized product.

`SharedCredentialLedger.create_after_allow` calls `save_decision` and `store_credential` in one `warrant.db.session.transaction(factory)` scope. Separately, `warrant.policy.persistence.persist_decision` also calls `save_decision`. Calling `persist_decision` and then `create_after_allow` for the same run currently attempts to insert the same run's decision twice, so the second path fails as a duplicate. The application must not assume these calls compose; no flow change is made here. The shared DB stores only the JWS signature segment, not the bearer token.

The fixture JWT format uses EdDSA and binds cart hash, merchant ID, integer amount, currency, expiry, nonce, issuer, audience, issue time, version, run ID, and approval hash. Public issuance remains blocked before signing until exact winner/cart binding is available. The mock gateway independently verifies token/cart/run and conditionally redeems the nonce plus approval hash in a fresh canonical transaction. `MockGateway` receives its clock through constructor injection; API callers cannot provide a verification time. The old local SQLite adapter now exists only in test support; runtime calls Ayush's canonical repositories.

**Authorization binding limitation:** Decision provenance carries `winner_fact_id`, but the cart contract does not define its mapping to stable `item_id`/`product_id`, actual seller, SKU or approved alternative, quantity, unit price, shipping, taxes, discounts, and final total. Therefore `issue_credential` fails closed even for an otherwise matching ALLOW. It creates no token and writes no credential. Public issuance remains unavailable until owners approve that mapping and its authoritative source.

The JWT includes the persisted `run_id`, and `MockGateway.authorize` requires the API caller's expected run ID. The gateway compares that value with the signed claim and redemption additionally compares it with the credential row under the ledger transaction. A missing or different run ID fails closed.

## Deepika API integration

The modules are framework-independent. API orchestration should call Stages 1–3, call `StabilityRunner.evaluate`, pass validated evidence to `decide`, and call `issue_credential` only for ALLOW; until winner/cart proof is available, the issuer intentionally rejects every otherwise eligible request. For gateway verification, pass the submitted credential, complete cart, and expected run ID. Convert failures to the API's standard error envelope without returning tokens, stack traces, secrets, or untrusted source content. HTTP endpoints and request/response schemas are not implemented in this branch.

## Ayush database integration

Migrations `0008_decision_product_provenance` and `0009_one_credential_per_run` add winner/approval fields and one-per-run uniqueness. Migration 0008 preflights historical ALLOW decisions and backfills a winner only when exactly one base ranking proves it; it aborts with affected IDs if proof is absent or ambiguous, does not fabricate approval hashes, and permits non-ALLOW rows without a winner. Migration 0009 checks duplicate run records and reports them without deleting or rewriting. Runtime uses `SharedCredentialLedger` to wrap the canonical repositories in shared transactions; redemption's conditional UPDATE is the first database operation of a fresh transaction. The raw-SQL adapter is test-only. Migration-backed tests passed under pinned dependencies.


### Mapping to the supplied teammate implementations

The provided Mayank archive uses `trussted` and has a duplicate database package; the provided Ayush archive's `warrant.db` contracts/repositories are canonical. Do not conflate Mayank's content-derived `ProductFact.fact_id` with stable product identity, or its `merchant_id` (currently derived from URL domain in an integration) with actual marketplace seller identity. Ayush requires a new per-extraction fact ID, seller ID, and nonempty SKU. Equivalent product identity is seller/SKU; missing SKU must fail mapping, and GTIN fallback is not approved. Mayank's `Decision.winner_fact_id` maps to base Ayush `RankingInput.winner_fact_id`, but Priyansh's current `RankingResult.winner_candidate_id` is not guaranteed to be that ID. Mayank decision reasons are structured objects; persistence needs an agreed conversion to reason-code strings.

Ayush's `CredentialInput` also contains the deterministic approval hash. `store_credential` enforces its equality with the persisted ALLOW decision; migration 0009 enforces one credential per run. Redemption compares all signature-bound fields against the persisted row in a single conditional update. Migration-backed tests passed.

Persisted ranking labels are `none`, `strip_persuasion`, and zero-based `shuffle_i`. Callback sub-run IDs are correlation values, never database run IDs. Stage 4 adapters now persist extraction facts, rankings, and complete stability reports through shared repositories when given explicit seller/SKU identity maps. Winner counts map to base-run fact IDs. Duplicate or missing identities fail closed. Skipped, failed, and timed-out reports record distinct stage states; failed-report payload details beyond safe reason codes cannot be stored in the current schema.

Mayank's archive does not provide enough output for a safe Stage 4 callback. Its `Observation` lacks typed retained fact/marketing/review/unclassified segments; its sanitizer emits flattened text without persuasion labels. Stage 4 cannot invent those labels. Mayank fact IDs use a content-derived observation ID plus product index, so they change across perturbations. Stage 4 currently requires candidate IDs to match exactly across runs and therefore rejects them rather than treating different IDs as identical. Integration requires separate per-run fact IDs and stable seller/SKU identity, typed source segments, and actual seller identity. Missing or nonunique SKU must fail mapping; GTIN fallback is not approved.

Mayank `ProductFact.sku` is optional while Ayush `ProductFactInput.sku` is required. Do not synthesize a SKU from fact ID or GTIN. Until owners agree how missing SKU products are represented, they are excluded from stable-identity mapping and fail closed.

Exact winner-to-cart validation is still unresolved. `DecisionInput` carries `winner_fact_id`, and the database stores the base winner provenance. The cart contract does not define how that fact maps to cart product identity, seller, quantity, or how shipping/additional charges map to the authorized total. Stage 6 must not guess that mapping. This needs an approved cross-team contract before issuance can be enabled.

### Cross-stage field mapping and current status

| Field | Source owner / source field | Adapter and database field | Consumer and validation | Status |
|---|---|---|---|---|
| Run ID | Orchestrator `run_id`; Stage 4 callback result run ID | Ayush `runs.id`; `rankings.run_id`, `stability_reports.run_id`, `decisions.run_id`, `credentials.run_id` | Stage 4 rejects wrong/duplicate/parent callback IDs; gateway checks signed and persisted run IDs | Field mapping known; runtime orchestration not integrated |
| Candidate ID | Priyansh `CandidateObservation.candidate_id` / `ProductFact.candidate_id` | No dedicated Ayush column; rankings store fact IDs | Stage 4 currently requires exact candidate membership across extractions | Must remain separate from database fact IDs; Mayank identity is not compatible |
| Fact ID | Mayank `ProductFact.fact_id`, regenerated from observation ID and product index | Ayush `ProductFactInput.id`; ranking order/winner reference same-run facts | Same-run foreign keys enforce DB ownership | Adapter persists only with explicit seller/SKU mapping; Mayank IDs alone are not stable identity |
| Stable product identity | Proposed seller/SKU pair from extracted fact | Ayush product fact `seller_id` + required `sku` | Use pair to correlate distinct perturbation facts; reject missing/ambiguous SKU | Partially represented; Mayank's SKU optional and merchant may be URL-derived |
| Winner fact ID | Mayank `Decision.winner_fact_id` / base rank winner | Ayush base `RankingInput.winner_fact_id` and `DecisionInput` | Same-run ownership enforced by repository and composite FK | Persisted; cart item mapping remains a blocker |
| Seller / merchant | Mayank `ProductFact.merchant_id`; current adapter `ProductFact.seller_id`; cart `merchant_id` | Ayush `seller_id`; decision has no seller | Stage 6 would compare actual seller, not infer it from hostname | Field semantics conflict; owner mapping required |
| SKU | Mayank `ProductFact.sku` (optional) | Ayush `ProductFactInput.sku` (required); `CartLine.sku` (optional) | Must match stable pair and cart line | Missing required SKU blocks correlation; no synthetic SKU |
| GTIN | Mayank `ProductFact.gtin` (optional) | Ayush product fact `gtin` (optional) | Additional cross-check only | No approved fallback to identity when SKU is absent |
| Quantity | User intent / trusted checkout | `CartLine.quantity`; absent from `ProductFact` and `DecisionInput` | Must equal approved intent and exactly one authorized line for MVP | No trusted source/contract |
| Unit price | Mayank `ProductFact.price: Money`; cart line `unit_price_minor` | Ayush `ProductFactInput.price_minor/currency`; not in decision winner binding | Compare integer minor units and currency | Fields exist, linkage to cart line not defined |
| Shipping | Mayank `ProductFact.shipping: Money` optional; cart `shipping_minor` | No decision binding field | Compare to approved total calculation | Cart/fact semantics and absent-value rule unresolved |
| Additional charges | Mayank `ProductFact.additional_charges: Money` optional; cart has tax/discount fields | No corresponding decision binding field | Compare to approved total calculation | Mapping unresolved |
| Total amount / currency | Mayank decision amount; current `PolicyInput` amount/currency | Ayush `DecisionInput.amount_minor/currency`; credential same fields | Stage 6 checks equality and strict minor-unit/currency types | Amount equality alone does not identify product |
| Stability state | Priyansh `StabilityReport.stable`; run ID and planned/failed counts | Ayush `StabilityInput.stable`, `threshold`, `winner_counts`, `flips` | Must map every winner to parent-run fact IDs and distinguish skipped from missing | Adapter persists successful reports when explicit identity mappings are supplied; failed/skipped details persist as stage state/reason |
| Policy result / reasons | Priyansh `Decision`; Mayank has a separate policy implementation | Ayush `DecisionInput.result/reasons/policy_version/winner_fact_id/approval_hash` | SHA-256 binds decision to its supplied evidence | `evaluate_same_run` validates typed stage evidence; the application must choose and consistently use one evaluator/write path |
| Credential ID / nonce | Priyansh `IssuedCredential.credential_id` / `nonce` | Ayush `CredentialInput.id` / unique `nonce` plus unique `run_id` migration | Nonce and run uniqueness; fresh-transaction single-use redemption | Adapter and migrations implemented and migration-backed tests passed; public issuance remains disabled |
| Cart hash | Priyansh canonical `warrant-cart-v1` cart bytes | Ayush `CredentialInput.cart_hash` | Gateway recalculates and compares the signed hash | Local behavior tested; no canonical repo integration test |

### Remaining integration contracts

- **Mayank / Stages 1–3:** The delivered selection DTO does not retain typed visible-content blocks or verified actual seller identity. Its fact and observation IDs are content-derived; SKU may be absent. The adapter therefore requires authoritative candidate and seller mappings. Stage 4 cannot rerun Mayank's extractor on persuasion-stripped content until the source-block contract is available. Do not infer seller or product identity from URL, fact ID, or GTIN.
- **Ayush / database:** `warrant.db` is the canonical runtime persistence implementation. The supplied repositories and migrations are present, and migration-backed tests pass. Database schema and repository ownership remain with Ayush; this branch does not add a competing persistence implementation.
- **Deepika / API:** The supplied archive contains a frontend, not backend routes or request models. API orchestration must build `SameRunEvidence` from trusted stage outputs and persistence reads. It must not accept policy booleans from a request or expose `create_after_allow`/`store_credential` as authorization endpoints.
- **Stage 7:** Receipt ownership and the event contract remain unconfirmed. This branch exposes typed outputs but does not implement a competing receipt system.

The exact winner-to-cart mapping remains undefined: the contract does not bind persisted winner fact and actual seller to cart product identity, quantity, unit price, or the treatment of shipping, tax, discounts, and other charges. No identity values should be synthesized.
## Stage 7 receipt integration

Stage 4 reports, Stage 5 decisions/reason codes, and Stage 6 issued credential metadata/gateway outcomes are immutable typed values that can be serialized by the receipt owner. The receipt owner should record the complete credential claims or a suitable credential fingerprint according to the receipt privacy policy, and must not record private keys or passphrases. No receipt event schema or signing chain is implemented here because Stage 7 ownership and exact event contract are unconfirmed.

## Current canonical persistence adapters and migrations

The current runtime path uses the `warrant.db` package supplied by Ayush. `warrant.credential.ledger.SharedCredentialLedger` is an application adapter only; it owns no DDL and contains no SQL statements. Credential issuance persistence calls `save_decision(session, DecisionInput)` followed by `store_credential(session, CredentialInput, now=...)` inside one `warrant.db.session.transaction(factory)` block. A transaction error rolls back both records. Redemption verifies the token and cart first, then uses a fresh shared transaction where `redeem_credential` is the first database operation; the gateway acts on success only after transaction commit.

The redemption repository gained a backwards-compatible optional `approval_hash` keyword predicate. The gateway always supplies it, so the one conditional UPDATE matches the stored approval identity in addition to nonce, unredeemed state, and expiry. Existing callers that omit the optional field retain the original repository behavior; the gateway does not omit it.

Forward-only Alembic revisions:

- `0008_decision_product_provenance` adds nullable `winner_fact_id` and `approval_hash` to decisions and `approval_hash` to credentials. Historical ALLOW rows are backfilled only from exactly one `rankings.perturbation='none'` winner. If that proof is missing or ambiguous, migration raises with affected decision/run IDs and changes no records. Historical approval hashes are not fabricated; their credentials remain unissuable. New ALLOW DTOs require both winner ID and approval hash, same-run ownership is validated by the repository and a composite foreign key, and the database check requires a winner.
- `0009_one_credential_per_run` checks existing credential counts before creating `UNIQUE(credentials.run_id)`. Duplicate records are reported without deletion or rewriting, and migration stops until an owner reconciles them.

`warrant.integrity.persistence.persist_perturbation_facts` requires caller-persisted parent-run observations and an exact `fact_id -> (seller_id, sku)` mapping. It stores distinct per-extraction facts through `save_product_facts`; missing/ambiguous SKU or mismatched identity fails. `candidate_fact_mapping` then maps stable identities to candidate keys explicitly. `persist_ranking` stores each ranking through `save_ranking`; the shared repository verifies its referenced facts belong to the parent run. `persist_stability_report` stores successful reports through `save_stability_report` with a versioned `flips` object containing sub-run correlation IDs, seeds, change flags, and mapped winners. It never treats a callback sub-run ID as a database run. Skipped, failed, and timed-out reports write the corresponding `StageState` through `record_stage_state`. The current schema has no place for the complete failed-report payload, so only its state and safe reason code persist.

The Stage 5 evaluator returns `winner_fact_id` and a deterministic SHA-256 `approval_hash`. `warrant.policy.persistence.persist_decision` calls Ayush's `save_decision`, whose repository validates same-run winner ownership. The `evaluate_same_run` builder derives inputs from typed stage outputs and explicit persisted-fact mappings, and rejects incomplete stability. Its DTOs are not cryptographic attestations; the API must assemble them from trusted outputs and persistence reads, never raw request booleans.

## Verification

Pinned dependency versions and the latest test/tool results are recorded in `docs/FINAL_IMPLEMENTATION_AND_SECURITY_AUDIT.md`.
