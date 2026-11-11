"""Stage 4–6 adapters exercise Ayush's migration-backed tables and repositories."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from tests.db.test_evidence import fact, observation, prepare
from tests.db.test_runs import start
from warrant.credential.cart import Cart, CartLine, cart_hash
from warrant.credential.gateway import MockGateway, RejectionCode
from warrant.credential.keys import KeyRing, SigningKey, VerificationKey
from warrant.credential.ledger import SharedCredentialLedger
from warrant.credential.token import (
    CredentialConfig,
    CredentialStoreError,
    IssuedCredential,
)
from warrant.db.contracts.evidence import (
    ObservationInput,
    ProductFactInput,
    RankingInput,
    SourceSpan,
)
from warrant.db.contracts.registry import BatchInput, FixtureInput, ScenarioInput, VariantInput
from warrant.db.errors import InvalidEvidence
from warrant.db.repositories.evidence import save_observations, save_product_facts, save_ranking
from warrant.db.repositories.registry import (
    create_batch,
    register_fixture,
    register_scenario,
    register_variant,
)
from warrant.db.repositories.runs import create_run
from warrant.db.session import (
    DbSettings,
    create_db_engine,
    create_session_factory,
    transaction,
)
from warrant.db.tables.credentials import CredentialRow
from warrant.db.tables.evidence import ProductFactRow, RankingRow
from warrant.db.tables.outcomes import DecisionRow, StabilityRow
from warrant.db.tables.runs import RunRow
from warrant.integrity.contracts import RankingResult
from warrant.integrity.engine import (
    PerturbationOutcome,
    PerturbationType,
    StabilityReport,
    StabilityRunner,
    StabilityState,
)
from warrant.integrity.persistence import (
    candidate_fact_mapping,
    persist_perturbation_facts,
    persist_ranking,
    persist_stability_report,
)
from warrant.policy.models import Decision, DecisionResult, ReasonCode


def test_stage4_rankings_and_stability_use_parent_run_fact_ids(
    factory: sessionmaker[Session], registry: None
) -> None:
    with transaction(factory) as session:
        prepare(session)
        base = RankingResult("run", "candidate-a", ("candidate-a",))
        persist_ranking(
            session,
            run_id="run",
            perturbation="none",
            ranking=base,
            fact_id_by_candidate_id={"candidate-a": "fact"},
            ranking_id="base-ranking",
        )
        persist_ranking(
            session,
            run_id="run",
            perturbation="shuffle_0",
            ranking=base,
            fact_id_by_candidate_id={"candidate-a": "fact"},
            ranking_id="shuffle-ranking",
        )
        report = StabilityReport(
            run_id="run",
            state=StabilityState.COMPLETED,
            skip_reason=None,
            baseline_winner_id="candidate-a",
            winner_counts=(("candidate-a", 2),),
            stable=True,
            threshold=1.0,
            planned_count=2,
            successful_count=2,
            failed_count=0,
            changed_count=2,
            shuffle_changed_count=1,
            outcomes=(
                PerturbationOutcome(
                    PerturbationType.STRIP_PERSUASION,
                    "strip-correlation-only",
                    None,
                    "candidate-a",
                    True,
                    True,
                ),
                PerturbationOutcome(
                    PerturbationType.SHUFFLE_ORDER,
                    "sub-run-correlation-only",
                    10,
                    "candidate-a",
                    True,
                    True,
                ),
            ),
            winner_flips=(),
            errors=(),
        )
        persist_stability_report(
            session,
            report=report,
            parent_run_id="run",
            base_fact_id_by_candidate_id={"candidate-a": "fact"},
            report_id="stability",
        )

    with factory() as session:
        rankings = session.scalars(select(RankingRow).order_by(RankingRow.id)).all()
        stability = session.get(StabilityRow, "stability")
        assert [(row.perturbation, row.winner_fact_id) for row in rankings] == [
            ("none", "fact"),
            ("shuffle_0", "fact"),
        ]
        assert stability is not None and stability.run_id == "run"
        assert "sub-run-correlation-only" in stability.flips
        assert "strip-correlation-only" in stability.flips


def test_stage4_rejects_cross_run_rank_candidate(
    factory: sessionmaker[Session], registry: None
) -> None:
    with transaction(factory) as session:
        prepare(session)
        with pytest.raises(InvalidEvidence):
            save_ranking(
                session,
                RankingInput(
                    id="ranking",
                    run_id="run",
                    perturbation="none",
                    ordered_fact_ids=("unknown-fact",),
                    scores={},
                    winner_fact_id="unknown-fact",
                ),
            )


def test_perturbed_fact_id_maps_to_parent_product_without_id_reuse(
    factory: sessionmaker[Session], registry: None
) -> None:
    with transaction(factory) as session:
        prepare(session)
        save_observations(session, (observation("perturbed-observation", "run"),))
        perturbed_fact = fact("shuffle-fact", "run").model_copy(
            update={"observation_id": "perturbed-observation"}
        )
        by_identity = persist_perturbation_facts(
            session,
            parent_run_id="run",
            facts=(perturbed_fact,),
            stable_identity_by_fact_id={"shuffle-fact": ("seller", "SKU-7")},
        )
        mapping = candidate_fact_mapping(
            candidate_id_by_identity={("seller", "SKU-7"): "candidate-a"},
            fact_id_by_identity=by_identity,
        )
        assert mapping == {"candidate-a": "shuffle-fact"}

    with factory() as session:
        assert session.get(ProductFactRow, "fact") is not None
        assert session.get(ProductFactRow, "shuffle-fact") is not None


def test_deliberate_skip_is_persisted_separately_from_missing_report(
    factory: sessionmaker[Session], registry: None
) -> None:
    with transaction(factory) as session:
        prepare(session)
        report = StabilityRunner.skipped(run_id="run", reason="cost_limit")
        assert (
            persist_stability_report(
                session,
                report=report,
                parent_run_id="run",
                base_fact_id_by_candidate_id={},
            )
            is None
        )
    with factory() as session:
        assert session.get(StabilityRow, "stability") is None
        run = session.get(RunRow, "run")
        assert run is not None
        assert '"state":"skipped"' in run.stage_states


def test_shared_credential_writer_persists_and_rolls_back_atomically(
    factory: sessionmaker[Session], registry: None
) -> None:
    approval_hash = "b" * 64
    decision = Decision(
        run_id="run",
        result=DecisionResult.ALLOW,
        reasons=(ReasonCode.CHECKS_PASSED,),
        policy_version="policy-1",
        amount_minor=1250,
        currency="USD",
        winner_fact_id="fact",
        approval_hash=approval_hash,
    )
    ledger = SharedCredentialLedger(factory, clock=lambda: NOW)
    with transaction(factory) as session:
        prepare(session)

    def issued(credential_id: str, nonce: str) -> IssuedCredential:
        return IssuedCredential(
            credential_id=credential_id,
            run_id="run",
            token="test-only-token",
            signature="test-only-signature",
            cart_hash="a" * 64,
            merchant_id="seller",
            amount_minor=1250,
            currency="USD",
            nonce=nonce,
            expires_at=NOW + timedelta(minutes=5),
            key_id="test-key",
            approval_hash=approval_hash,
        )

    ledger.create_after_allow(decision=decision, credential=issued("credential-1", "nonce-1"))
    with pytest.raises(CredentialStoreError):
        ledger.create_after_allow(decision=decision, credential=issued("credential-2", "nonce-2"))

    with factory() as session:
        stored_decision = session.scalar(select(DecisionRow).where(DecisionRow.run_id == "run"))
        assert stored_decision is not None
        assert stored_decision.winner_fact_id == "fact"
        assert stored_decision.approval_hash == approval_hash
        assert session.scalar(select(func.count()).select_from(CredentialRow)) == 1
    assert (
        ledger.redeem_once(
            nonce="nonce-1",
            run_id="run",
            signature="test-only-signature",
            cart_hash="a" * 64,
            merchant_id="seller",
            amount_minor=1250,
            currency="USD",
            approval_hash=approval_hash,
            now=NOW,
        ).value
        == "REDEEMED"
    )
    assert (
        ledger.redeem_once(
            nonce="nonce-1",
            run_id="run",
            signature="test-only-signature",
            cart_hash="a" * 64,
            merchant_id="seller",
            amount_minor=1250,
            currency="USD",
            approval_hash=approval_hash,
            now=NOW,
        ).value
        == "REJECTED"
    )


def test_failed_shared_credential_transaction_rolls_back_decision(
    factory: sessionmaker[Session], registry: None
) -> None:
    approval_hash = "c" * 64
    decision = Decision(
        run_id="run",
        result=DecisionResult.ALLOW,
        reasons=(ReasonCode.CHECKS_PASSED,),
        policy_version="policy-1",
        amount_minor=1250,
        currency="USD",
        winner_fact_id="fact",
        approval_hash=approval_hash,
    )
    credential = IssuedCredential(
        credential_id="expired-credential",
        run_id="run",
        token="test-only-token",
        signature="test-only-signature",
        cart_hash="a" * 64,
        merchant_id="seller",
        amount_minor=1250,
        currency="USD",
        nonce="expired-nonce",
        expires_at=NOW,
        key_id="test-key",
        approval_hash=approval_hash,
    )
    with transaction(factory) as session:
        prepare(session)
    with pytest.raises(InvalidEvidence):
        SharedCredentialLedger(factory, clock=lambda: NOW).create_after_allow(
            decision=decision, credential=credential
        )
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(DecisionRow)) == 0
        assert session.scalar(select(func.count()).select_from(CredentialRow)) == 0


def test_shared_gateway_checks_signed_approval_hash_before_atomic_redemption(
    factory: sessionmaker[Session], registry: None
) -> None:
    config = CredentialConfig("warrant-integration-test")
    private = Ed25519PrivateKey.generate()
    signing = SigningKey("integration-key", private)
    key_ring = KeyRing((VerificationKey(signing.key_id, private.public_key()),))
    cart = Cart(
        merchant_id="seller",
        amount_minor=1250,
        currency="USD",
        items=(CartLine("synthetic-item", 1, 1250, "SKU-7"),),
    )
    approval_hash = "e" * 64
    with transaction(factory) as session:
        prepare(session)
    decision = Decision(
        run_id="run",
        result=DecisionResult.ALLOW,
        reasons=(ReasonCode.CHECKS_PASSED,),
        policy_version="policy-1",
        amount_minor=1250,
        currency="USD",
        winner_fact_id="fact",
        approval_hash=approval_hash,
    )
    issued_at = int(NOW.timestamp())
    expires_at = NOW + timedelta(minutes=5)
    claims = {
        "amount_minor": cart.amount_minor,
        "approval_hash": approval_hash,
        "aud": config.audience,
        "cart_hash": cart_hash(cart),
        "currency": cart.currency,
        "exp": int(expires_at.timestamp()),
        "iat": issued_at,
        "iss": config.issuer,
        "jti": "integration-nonce",
        "merchant_id": cart.merchant_id,
        "run_id": "run",
        "v": 1,
    }
    token = jwt.encode(
        claims,
        private,
        algorithm="EdDSA",
        headers={"kid": signing.key_id, "typ": "JWT"},
    )
    credential = IssuedCredential(
        credential_id="integration-credential",
        run_id="run",
        token=token,
        signature=token.rsplit(".", 1)[1],
        cart_hash=cart_hash(cart),
        merchant_id=cart.merchant_id,
        amount_minor=cart.amount_minor,
        currency=cart.currency,
        nonce="integration-nonce",
        expires_at=expires_at,
        key_id=signing.key_id,
        approval_hash=approval_hash,
    )
    ledger = SharedCredentialLedger(factory, clock=lambda: NOW)
    ledger.create_after_allow(decision=decision, credential=credential)
    gateway = MockGateway(
        config=config,
        key_ring=key_ring,
        ledger=ledger,
        clock=lambda: NOW + timedelta(seconds=1),
    )
    forged_claims = claims | {"approval_hash": "f" * 64}
    forged_token = jwt.encode(
        forged_claims,
        private,
        algorithm="EdDSA",
        headers={"kid": signing.key_id, "typ": "JWT"},
    )
    assert (
        gateway.authorize(token=forged_token, cart=cart, run_id="run").code
        is RejectionCode.CREDENTIAL_NOT_ISSUED
    )
    assert gateway.authorize(token=token, cart=cart, run_id="run").accepted is True
    assert gateway.authorize(token=token, cart=cart, run_id="run").accepted is False


def test_concurrent_shared_issuance_is_serialized_by_canonical_database(tmp_path) -> None:
    from warrant.db.migrate import migrate

    engine = create_db_engine(DbSettings(url=f"sqlite:///{(tmp_path / 'shared.db').as_posix()}"))
    migrate(engine)
    factory = create_session_factory(engine)
    try:
        with transaction(factory) as session:
            register_scenario(
                session,
                ScenarioInput(
                    id="attack",
                    scenario_key="attack",
                    title="attack",
                    kind="attack",
                    definition={},
                    expected_outcome="synthetic",
                    version=1,
                ),
            )
            register_fixture(
                session,
                FixtureInput(
                    id="attack-page",
                    scenario_id="attack",
                    name="page",
                    content_hash="a" * 64,
                    path="attack.html",
                    created_at=NOW,
                ),
            )
            register_variant(
                session,
                VariantInput(
                    id="variant",
                    name="warrant",
                    model_name="synthetic",
                    model_version="1",
                    prompt_version="1",
                    config={},
                ),
            )
            create_batch(session, BatchInput(id="batch", created_at=NOW, git_commit="test", seed=1))
            create_run(session, start())
            save_observations(
                session,
                (
                    ObservationInput(
                        id="observation",
                        run_id="run",
                        url="https://synthetic.invalid/item",
                        content_hash="b" * 64,
                        byte_size=1,
                        fetched_at=NOW,
                    ),
                ),
            )
            save_product_facts(
                session,
                (
                    ProductFactInput(
                        id="fact",
                        run_id="run",
                        observation_id="observation",
                        sku="SKU-1",
                        name="Synthetic item",
                        price_minor=1250,
                        currency="USD",
                        spec={},
                        seller_id="seller-1",
                        source_span=SourceSpan(start=0, end=1),
                    ),
                ),
            )
        approval_hash = "d" * 64
        decision = Decision(
            run_id="run",
            result=DecisionResult.ALLOW,
            reasons=(ReasonCode.CHECKS_PASSED,),
            policy_version="policy-1",
            amount_minor=1250,
            currency="USD",
            winner_fact_id="fact",
            approval_hash=approval_hash,
        )
        ledger = SharedCredentialLedger(factory, clock=lambda: NOW)
        barrier = Barrier(2)

        def issue(index: int) -> bool:
            credential = IssuedCredential(
                credential_id=f"credential-{index}",
                run_id="run",
                token="test-token",
                signature="test-signature",
                cart_hash="c" * 64,
                merchant_id="seller-1",
                amount_minor=1250,
                currency="USD",
                nonce=f"nonce-{index}",
                expires_at=NOW + timedelta(minutes=5),
                key_id="test-key",
                approval_hash=approval_hash,
            )
            barrier.wait(timeout=5)
            try:
                ledger.create_after_allow(decision=decision, credential=credential)
                return True
            except CredentialStoreError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(issue, (1, 2)))
        assert sum(outcomes) == 1
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(CredentialRow)) == 1
            assert session.scalar(select(func.count()).select_from(DecisionRow)) == 1
    finally:
        engine.dispose()
