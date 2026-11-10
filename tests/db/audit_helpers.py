"""Synthetic audit fixtures; the real signature verifier is an external integration."""

from datetime import timedelta

from sqlalchemy.orm import Session

from tests.db.conftest import NOW
from tests.db.test_runs import start
from trussted.db.contracts.receipts import FinalizedReceipt, ReceiptEventInput, SigningKeyInput
from trussted.db.contracts.registry import BatchInput, FixtureInput, ScenarioInput, VariantInput
from trussted.db.repositories.receipts import register_signing_key
from trussted.db.repositories.registry import (
    create_batch,
    register_fixture,
    register_scenario,
    register_variant,
)
from trussted.db.repositories.runs import create_run


def receipt_bundle() -> FinalizedReceipt:
    """Use hand-chosen envelope hashes; only external crypto verification is stubbed."""
    return FinalizedReceipt(
        id="receipt",
        run_id="run",
        final_hash="c" * 64,
        signature="external-signature",
        signing_key_id="key",
        created_at=NOW + timedelta(seconds=2),
        export_path="receipt.json",
        events=(
            ReceiptEventInput(
                id="event-0",
                receipt_id="receipt",
                seq=0,
                type="intent",
                payload={},
                payload_hash="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                prev_hash="0" * 64,
                event_hash="b" * 64,
                created_at=NOW,
            ),
            ReceiptEventInput(
                id="event-1",
                receipt_id="receipt",
                seq=1,
                type="decision",
                payload={},
                payload_hash="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                prev_hash="b" * 64,
                event_hash="c" * 64,
                created_at=NOW + timedelta(seconds=1),
            ),
        ),
    )


def accept_external_signature(bundle: FinalizedReceipt) -> None:
    """Stand in only for the receipt owner's unavailable crypto verifier."""


def prepare_receipt(session: Session) -> None:
    create_run(session, start())
    register_signing_key(
        session,
        SigningKeyInput(id="key", algorithm="ed25519", public_key="public-bytes", created_at=NOW),
    )


def prepare_minimal_registry(session: Session) -> None:
    """Register synthetic parents for independent file-backed migration tests."""
    register_scenario(
        session,
        ScenarioInput(
            id="attack",
            scenario_key="attack",
            title="attack",
            kind="attack",
            definition={},
            expected_outcome="synthetic expected outcome",
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
            name="trussted",
            model_name="stub",
            model_version="1",
            prompt_version="1",
            config={},
        ),
    )
    create_batch(session, BatchInput(id="batch", created_at=NOW, git_commit="abc", seed=1))
