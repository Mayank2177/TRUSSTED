"""Completed receipt inputs; signing and envelope verification belong to their owner."""

from typing import Annotated, Literal, Protocol

from pydantic import AwareDatetime, Field, JsonValue, StrictInt, StringConstraints

from trussted.db.contracts import FrozenModel, Hash, Id

type NonemptyText = Annotated[str, StringConstraints(strict=True, min_length=1)]


class SigningKeyInput(FrozenModel):
    """Public verification metadata only; private key material is never accepted."""

    id: Id
    algorithm: Literal["ed25519"]
    public_key: NonemptyText
    created_at: AwareDatetime
    revoked_at: AwareDatetime | None = None


class ReceiptEventInput(FrozenModel):
    """One canonical payload and the receipt owner's signed-envelope chain hashes."""

    id: Id
    receipt_id: Id
    seq: Annotated[StrictInt, Field(ge=0)]
    type: Literal[
        "intent",
        "observation",
        "facts",
        "conflicts",
        "ranking",
        "stability",
        "decision",
        "credential",
        "settlement",
    ]
    payload: JsonValue
    payload_hash: Hash
    prev_hash: Hash
    event_hash: Hash
    created_at: AwareDatetime


class FinalizedReceipt(FrozenModel):
    """A fully signed bundle, inserted once together with all of its events."""

    id: Id
    run_id: Id
    final_hash: Hash
    signature: NonemptyText
    signing_key_id: Id
    created_at: AwareDatetime
    export_path: NonemptyText
    events: tuple[ReceiptEventInput, ...]


class ReceiptVerifier(Protocol):
    """Verify real signatures and canonical envelopes; raise InvalidEvidence on failure."""

    def __call__(self, bundle: FinalizedReceipt) -> None:
        """Verify a completed bundle without mutating it."""
        ...


class ReceiptDetail(FrozenModel):
    """Detached complete receipt with retained public-key and revocation metadata."""

    bundle: FinalizedReceipt
    signing_key: SigningKeyInput
