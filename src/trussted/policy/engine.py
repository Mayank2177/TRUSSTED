"""Decision policy: turns a SelectionResult into ALLOW / STEP_UP / BLOCK. Deterministic.

Also re-checks the winner's hard limits independently of the ranker (defence in depth).
"""

from __future__ import annotations

from ..config import PolicyConfig
from ..models.decision import Decision, DecisionResult, Reason, ReasonCode
from ..models.intent import UserIntent
from ..models.results import SelectionResult
from ..rank.scorer import total_cost

D = DecisionResult
R = ReasonCode


class DecisionPolicy:
    def __init__(self, config: PolicyConfig) -> None:
        self._cfg = config

    def decide(self, intent: UserIntent, selection: SelectionResult) -> Decision:
        cfg = self._cfg
        reasons: list[Reason] = []
        err_result = D(cfg.stage_error_result)

        for err in selection.stage_errors:
            reasons.append(Reason(R.STAGE_ERROR, f"{err.stage}:{err.ref}: {err.message}", err_result))

        cand = selection.winner_candidate
        if cand is None:
            reasons.append(Reason(R.NO_ELIGIBLE_CANDIDATE,
                                  f"{len(selection.ranking.disqualified)} candidate(s) disqualified",
                                  D.BLOCK))
            return self._finish(reasons, None, None)

        fact = cand.fact
        total = cand.total_cost

        # -- independent re-check of hard limits ------------------------------------------
        if total.currency != intent.currency or fact.price.currency != intent.currency:
            reasons.append(Reason(R.RECHECK_CURRENCY, f"{total.currency} != {intent.currency}", D.BLOCK))
        else:
            if intent.max_total is not None and total > intent.max_total:
                reasons.append(Reason(R.RECHECK_BUDGET, f"{total} > {intent.max_total}", D.BLOCK))
            if total != total_cost(fact, intent.quantity):
                reasons.append(Reason(R.RECHECK_TOTAL, "ranked total differs from recomputed total",
                                      D.BLOCK))

        ver = next((v for v in selection.verifications if v.fact_id == fact.fact_id), None)
        if ver is not None and ver.conflicts:
            fields = ", ".join(sorted({c.field for c in ver.conflicts}))
            worst = D.BLOCK if ver.has_high_conflict else D.STEP_UP
            reasons.append(Reason(R.FACT_CONFLICT, fields, worst))

        amount = total.to_decimal()
        if (ver is None or not ver.independent_sources) and cfg.require_reference_above is not None \
                and amount >= cfg.require_reference_above:
            reasons.append(Reason(R.NO_INDEPENDENT_REFERENCE,
                                  f"{total} with no independent source", D.STEP_UP))

        for flag in cand.flags:
            if flag.value in cfg.step_up_flags and flag.value != "CONFLICT_PRESENT":
                reasons.append(Reason(R.RISK_FLAG, flag.value, D.STEP_UP))

        obs = next((o for o in selection.observations if o.observation_id == fact.observation_id), None)
        if obs is not None:
            for flag in obs.flags:
                if flag in cfg.step_up_page_flags:
                    reasons.append(Reason(R.PAGE_FLAG, flag, D.STEP_UP))

        margin = selection.ranking.winner_margin
        if cfg.min_winner_margin is not None and margin is not None and margin < cfg.min_winner_margin:
            reasons.append(Reason(R.CLOSE_CALL, f"score margin {margin}", D.STEP_UP))

        if cfg.step_up_total_above is not None and amount > cfg.step_up_total_above:
            reasons.append(Reason(R.HIGH_VALUE, f"{total} > {cfg.step_up_total_above}", D.STEP_UP))

        return self._finish(reasons, fact.fact_id, total)

    def _finish(self, reasons: list[Reason], fact_id: str | None, total) -> Decision:  # type: ignore[no-untyped-def]
        if any(r.result is D.BLOCK for r in reasons):
            result = D.BLOCK
        elif any(r.result is D.STEP_UP for r in reasons):
            result = D.STEP_UP
        else:
            result = D.ALLOW
            reasons = [*reasons, Reason(R.CLEAN, "no risk signals", D.ALLOW)]
        return Decision(result, tuple(reasons), fact_id, total, self._cfg.policy_version)
