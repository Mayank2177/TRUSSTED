"""Independent WAL sessions atomically race to consume the same nonce."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from tests.db.conftest import NOW
from tests.db.test_credentials import allow_decision, credential
from tests.db.test_runs import start
from warrant.db.contracts.registry import BatchInput, ScenarioInput, VariantInput
from warrant.db.migrate import migrate
from warrant.db.repositories.credentials import redeem_credential, store_credential
from warrant.db.repositories.registry import create_batch, register_scenario, register_variant
from warrant.db.repositories.runs import create_run
from warrant.db.session import DbSettings, create_db_engine, create_session_factory, transaction


def test_exactly_one_concurrent_redemption_succeeds(tmp_path: Path) -> None:
    engine = create_db_engine(DbSettings(url=f"sqlite:///{(tmp_path / 'race.db').as_posix()}"))
    try:
        migrate(engine)
        factory = create_session_factory(engine)
        with transaction(factory) as session:
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
            register_variant(
                session,
                VariantInput(
                    id="variant",
                    name="warrant",
                    model_name="stub",
                    model_version="1",
                    prompt_version="1",
                    config={},
                ),
            )
            create_batch(session, BatchInput(id="batch", created_at=NOW, git_commit="abc", seed=1))
            create_run(session, start().model_copy(update={"input_manifest": ()}))
            allow_decision(session)
            store_credential(session, credential(), now=NOW)
        barrier = Barrier(2)

        def consume() -> bool:
            barrier.wait(timeout=10)
            with transaction(factory) as session:
                result = redeem_credential(session, nonce="nonce", now=NOW)
            return result

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: consume(), range(2)))
        assert sorted(results) == [False, True]
    finally:
        engine.dispose()
