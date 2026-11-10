# TRUSSTED

Research prototype for shopping-agent decision integrity. The working Python package is `warrant`.

This branch implements Ayush's database contribution: local SQLite, SQLAlchemy models, Alembic migrations, reproducible seeds, typed repositories, immutable receipt storage and single-use simulated credentials.

```powershell
uv sync --locked
uv run warrant db migrate
uv run warrant db seed --scenario-dir examples/db/scenarios --fixture-root examples/db/fixtures
uv run pytest -m "not bench"
```

The default database is `data/warrant.db` on the computer running the backend. A teammate recording a local demo creates their own database; Ayush's PC can be off. Runtime DB files are ignored by Git.

- [Setup and demo handoff](docs/database-setup.md)
- [Pipeline/API database contract](docs/database-contract.md)
- [Implementation plan](docs/superpowers/plans/2026-11-09-ayush-database-implementation.md)
- [Project requirements](docs/reference/PRD.md)

The sample seed demonstrates database setup, not measured security effectiveness. Pipeline algorithms, the real receipt signature/envelope verifier, API, frontend and full benchmark corpus are separate team integrations. No real payment processing is included. Receipts establish record integrity only when verified; they do not establish truth of source data or issuer acceptance. Consistently poisoned facts remain a documented limitation; synthetic benchmark results do not establish open-web coverage.
