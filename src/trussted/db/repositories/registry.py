"""Immutable registry registration with exact replay semantics."""

from sqlalchemy.orm import Session

from trussted.db.base import Base
from trussted.db.contracts.registry import BatchInput, FixtureInput, ScenarioInput, VariantInput
from trussted.db.errors import DuplicateRecord, InvalidEvidence, flush
from trussted.db.tables.registry import BatchRow, FixtureRow, ScenarioRow, VariantRow
from trussted.db.values import canonical_json, sha256_hex, utc_text


def _register(session: Session, row: Base, values: dict[str, object], identity: str) -> str:
    existing = session.get(type(row), identity)
    if existing is not None:
        if all(getattr(existing, key) == value for key, value in values.items()):
            return identity
        raise DuplicateRecord(f"Registry identity {identity!r} already has a different definition")
    session.add(row)
    flush(session)
    return identity


def register_scenario(session: Session, value: ScenarioInput) -> str:
    values = dict(value.model_dump(), definition=canonical_json(value.definition))
    return _register(session, ScenarioRow(**values), values, value.id)


def register_fixture(session: Session, value: FixtureInput) -> str:
    values = dict(value.model_dump(), created_at=utc_text(value.created_at))
    return _register(session, FixtureRow(**values), values, value.id)


def register_variant(session: Session, value: VariantInput) -> str:
    envelope = {
        "name": value.name,
        "model_name": value.model_name,
        "model_version": value.model_version,
        "prompt_version": value.prompt_version,
        "config": value.config,
    }
    config_hash = sha256_hex(canonical_json(envelope).encode("utf-8"))
    if value.config_hash is not None and value.config_hash != config_hash:
        raise InvalidEvidence("Variant config_hash does not match its full versioned envelope")
    values = dict(value.model_dump(), config=canonical_json(value.config), config_hash=config_hash)
    return _register(session, VariantRow(**values), values, value.id)


def create_batch(session: Session, value: BatchInput) -> str:
    values = dict(value.model_dump(), created_at=utc_text(value.created_at))
    return _register(session, BatchRow(**values), values, value.id)
