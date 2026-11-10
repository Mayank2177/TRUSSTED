# Trussted: verify an AI shopping agent's purchase before money moves

Pipeline: **extract -> cross-check -> rank -> policy -> PayPal sandbox approval**.
Given a `UserIntent` and fetched pages, Trussted extracts grounded product facts, compares them
with independent sources, ranks eligible candidates deterministically, and returns
`ALLOW` / `STEP_UP` / `BLOCK` with reasons. Only non-BLOCK decisions can create a PayPal order,
and capture happens only after the buyer approves **and** the order amount still matches.

```
src/trussted/
  models/        frozen, validated dataclasses (UserIntent, ProductFact, Decision, ...)
  llm/           provider interface, StubClient, CassetteClient (record/replay), AnthropicClient
  extract/       sanitiser, JSON-LD parser, prompt (prompts/extraction_v1.txt), grounded extraction
  verify/        cross-check vs page structured data and independent reference sources
  rank/          deterministic scorer (hard constraints disqualify; weights rank survivors)
  policy/        ALLOW / STEP_UP / BLOCK + independent re-check of hard limits
  integrations/  Channel3 (discovery + independent price reference), PayPal Orders v2 (sandbox)
  pipeline.py    stages 1-3 orchestration with per-page error isolation
```

Zero runtime dependencies (stdlib, Python 3.12+). Specs mention Pydantic; validated frozen
dataclasses were used so everything is testable offline.

## Run
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t .     # 53 tests
PYTHONPATH=src python3 examples/demo_offline.py               # no keys needed
```

## Real integrations (set env vars from .env.example)
```python
from trussted.config import Settings, PayPalConfig
from trussted.integrations import Channel3Client, Channel3Reference, PayPalClient
from trussted.llm.anthropic_client import AnthropicClient       # pip install .[anthropic]
from trussted.pipeline import SelectionPipeline
from trussted.policy import DecisionPolicy

s = Settings.from_env()
c3 = Channel3Client(s.channel3)
pipe = SelectionPipeline.build(AnthropicClient(s.llm), [Channel3Reference(c3)], s)
selection = pipe.run(intent, pages)
decision = DecisionPolicy(s.policy).decide(intent, selection)
if decision.result.value != "BLOCK":
    pp = PayPalClient(PayPalConfig(return_url="https://you/ok", cancel_url="https://you/no"))
    order = pp.create_order(decision, selection.winner_candidate, intent.quantity)
    # send the buyer to order.approve_url, then:
    pp.capture_order(order.order_id, decision.amount)
```
STEP_UP means a human must review the decision **before** you create the order.

## Design notes
- The LLM is untrusted and sees only sanitised visible text. Each extracted record must quote
  verbatim evidence from the page that contains its price, else it is rejected.
- "verified" requires an independent reference; the page agreeing with itself does not count.
- Ranking is a pure function (no LLM, input-order independent). Price/delivery use ratio-to-best
  scoring so near-equal offers stay near-equal (this powers the policy's close-call check).
- Fail closed: stage errors surface as `StageError`s and force STEP_UP/BLOCK in policy.
- PayPal: sandbox by default; live requires `allow_live=True`. Order creation is idempotent via
  `PayPal-Request-Id`, refuses BLOCK decisions and any decision/cart mismatch.
- Every threshold, severity, alias and prompt is configuration (`config.py`).

## Not verified / known limits (read before the demo)
1. **No live API runs.** Channel3 and PayPal adapters follow their public docs and are tested
   against fakes only. Channel3 docs show several offer shapes; parsing is tolerant but you
   must run one real search/lookup. Check PayPal's `payment_source.paypal.experience_context`
   fields against developer.paypal.com for your sandbox app.
2. `AnthropicClient` is untested against the live API.
3. Facts that page and reference falsify consistently are not detected.
4. Channel3-derived candidates have no independent reference (policy steps up above the
   configured amount) and may lack specs, so spec-constrained intents can disqualify them.
5. Not included: page fetching, HTTP server/Render deployment, UI, perturbation check,
   cart-bound tokens, receipts.
6. No effectiveness measurement yet: tests prove behaviour, not that it reduces real fraud.
