# Database setup and demo handoff

This is Ayush's database/persistence contribution to TRUSSTED. The Python package keeps the working name `warrant`. The pipeline, real receipt verifier, API and frontend are supplied by their owners.

## Where data lives

The default database is `data/warrant.db`, relative to the directory where the backend/CLI runs. Run commands from the repository root. SQLite also creates local `-wal`/`-shm` sidecar files while active. All are ignored by Git.

On Ayush's current checkout the default resolves to `C:\Users\Ayush Paul\Desktop\paypal\data\warrant.db`. On Mayank's laptop it resolves inside Mayank's checkout. His demo does not require Ayush's PC to be on. GitHub distributes code, migrations and synthetic fixtures; it does not synchronize runtime database records between laptops.

Each demo recorder runs the backend and SQLite on their own laptop. A shared online backend/database would be a separate deployment decision. SQLite records are local until the team explicitly deploys a backend somewhere else.

## Fresh checkout

Use Python 3.12 and Git. While the contribution is under review, check out `feat/ayush-db`; after it is merged use `main`.

```powershell
git clone https://github.com/Mayank2177/TRUSSTED.git
cd TRUSSTED
git switch feat/ayush-db
py -3.12 -m pip install uv==0.13.5
py -3.12 -m uv sync --locked
py -3.12 -m uv run warrant db migrate
py -3.12 -m uv run warrant db seed --scenario-dir examples/db/scenarios --fixture-root examples/db/fixtures
```

If `uv` is already installed, use `uv` in place of `py -3.12 -m uv`. On Linux/macOS use `python3.12` instead of `py -3.12`. No separate database server, cloud account, live model key or payment key is needed for these commands.

The sample is a single benign `DB_DEMO` scenario with two fictional fixture files. It demonstrates storage setup, not a security evaluation. A second identical seed returns `scenarios_created: 0`, `fixtures_created: 0`, `unchanged: 3`. The benchmark owner supplies the actual S1-S7/B1-B5 corpus; it is not replaced by this sample.

For the already prepared Ayush workspace, the installed executable works directly:

```powershell
.\.venv\Scripts\warrant.exe db migrate
.\.venv\Scripts\warrant.exe db seed --scenario-dir examples/db/scenarios --fixture-root examples/db/fixtures
```

## Choose a different local file

```powershell
$env:WARRANT_DB_URL = "sqlite:///data/demo-recording.db"
uv run warrant db migrate
uv run warrant db seed --scenario-dir examples/db/scenarios --fixture-root examples/db/fixtures
```

The CLI also accepts `warrant --db-url "sqlite:///data/other.db" db migrate`. `WARRANT_DB_URL` must be set in the running process. `.env.example` lists its name; the application does not automatically load `.env` files. With the variable unset, the default is `sqlite:///data/warrant.db`.

Use a different file for experiments rather than deleting a database containing runs you want to keep. To copy an active database, use a proper SQLite backup or stop all app processes first; copying only the `.db` file while WAL writes are active can miss data.

## Migrations and seeding

`warrant db migrate` applies the six Alembic revisions and creates 15 application tables. `alembic_version` is Alembic's additional bookkeeping table. Runtime startup does not silently invent tables.

```powershell
uv run alembic current
uv run alembic upgrade head
```

Keep applied revisions unchanged; add a new migration for later changes. Later SQLite table rebuilds must preserve/recreate custom constraints and receipt/scenario triggers. PostgreSQL-style types are used where possible, but PostgreSQL deployment and equivalent trigger enforcement have not been tested.

Seeding loads YAML definitions and registers fixture bytes by SHA-256 hash. Files stay on disk. The loader rejects paths outside the fixture root, hash mismatches, changed content under an existing revision and duplicate identities. Increment a scenario's version when its fixture set or definition changes.

## Minimal pipeline integration

Configure a factory once at backend startup. Create a new Session per request/task; never share Sessions between threads. Dispose the engine at shutdown.

```python
import os
from warrant.db.session import DbSettings, create_db_engine, create_session_factory, transaction

engine = create_db_engine(DbSettings(url=os.getenv("WARRANT_DB_URL", "sqlite:///data/warrant.db")))
factory = create_session_factory(engine)

# Input is a validated DTO supplied by the owning pipeline stage.
with transaction(factory) as session:
    # create_run(session, run_start) or save_decision(session, decision)
    pass
```

Create a run and commit before external LLM/network work. Persist each stage in a short transaction. Repository functions flush but never commit. Let storage exceptions escape `transaction(...)` so it rolls back the entire stage. The pipeline boundary handles those failures as STEP_UP/BLOCK; DB code never chooses ALLOW.

Use `get_run_detail`, `list_runs`, `get_receipt`, `get_benchmark_counts` and `get_benchmark_samples` through repository modules. They return validated objects; API callers do not receive lazy SQLAlchemy relationships.

See [database-contract.md](database-contract.md) for exact inputs and ownership. [The cross-module storage test](../tests/db/test_db_handoff.py) is an executable integration example. It replaces only the unavailable external receipt verifier; it is not evidence that real receipt signatures verify.

## Validation

```powershell
uv sync --locked
uv run pytest -m "not bench"
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict src
```

Ordinary tests use isolated in-memory databases. Migration/WAL/concurrency tests use temporary file databases. The bounded temporary test path is `.tools/pytest`, ignored by Git; parallel test processes must override `--basetemp` with distinct directories. No live LLM/network is used by tests. Windows and Ubuntu checks are configured in the database GitHub Actions workflow; a local Windows run does not establish that remote CI has passed.

## Integration still owned by the team

- Assign the receipt owner and wire their canonical event-envelope/Ed25519 verifier into `save_finalized_receipt(..., verify=...)`. The repository requires this callback and checks chain structure/payload hashes independently; no production no-op verifier is provided.
- Mayank/Priyansh adapt their models to the documented DTOs, including explicit SKU, perturbation identity and source-span convention.
- Deepika supplies API routes and Session dependencies; the frontend uses that API.
- The benchmark owner supplies the real corpus, outcome labels and confidence-interval/reporting code.

The database implementation does not evaluate attack resistance, process real money or implement the demo frontend.
