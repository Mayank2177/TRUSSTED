# CODE_STYLE.md

Goal: readable, typed, deterministic code that a reviewer can trust. Applies to Python (core) and TypeScript (dashboard).

## 1. Tooling (enforced in CI)

| Tool | Purpose | Command |
|---|---|---|
| `ruff format` | formatting | `uv run ruff format .` |
| `ruff check` | lint + import sort | `uv run ruff check .` |
| `mypy --strict` | type checking | `uv run mypy src` |
| `pytest` | tests | `uv run pytest` |
| `eslint` + `prettier` + `tsc --noEmit` | dashboard | `pnpm lint && pnpm typecheck` |

Line length 100. Pre-commit runs format, lint, and mypy on changed files. CI fails on any warning.

## 2. Python conventions

- Python 3.12. Type hints on **all** function signatures and public attributes. No `Any` without a comment explaining why.
- Data crossing module boundaries is a **Pydantic model** or frozen `dataclass`, never a bare `dict`.
- Prefer pure functions. Side effects (IO, DB, network, LLM, clock, randomness) live at the edges and are injected.
- Time and randomness are injected (`clock: Callable[[], datetime]`, `rng: random.Random`) so tests are deterministic.
- Money is `Decimal` (or integer minor units) with an explicit currency. **Never `float`.**
- Naming: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants, `_private` prefix for internals. Booleans read as questions: `is_stable`, `has_conflict`.
- Modules under ~300 lines; functions under ~40 lines. Split before exceeding.
- No wildcard imports. No circular imports. `models/` imports nothing from other `trussted` packages.
- Docstrings (Google style) on public functions and classes: what, args, returns, raises. Do not restate the type hints.
- Comments explain **why**, not what.

## 3. Error handling

- Define a small exception hierarchy in `trussted/errors.py`: `TrusstedError` -> `ExtractionError`, `VerificationError`, `PolicyError`, `ReceiptError`, `CredentialError`.
- **Fail closed:** catch at the pipeline boundary and convert to a `STEP_UP` decision with a reason code. Never swallow exceptions silently; never default to `ALLOW`.
- Use `raise ... from err` to keep causes. No bare `except:`.
- Validate at boundaries (API input, LLM output, file input). Trust nothing from the LLM.

## 4. Logging

- `structlog` JSON logs. Include `run_id`, `stage`, `scenario_id`.
- Never log secrets, private keys, full page HTML, or anything resembling card data. Log hashes instead.
- Levels: `DEBUG` internals, `INFO` stage transitions, `WARNING` degraded behaviour, `ERROR` stage failure.

## 5. LLM-specific rules

- All LLM calls go through `LLMClient`. No direct provider SDK calls elsewhere.
- Prompts live in `src/trussted/extract/prompts/` as versioned text files, not inline strings. Each has a `PROMPT_VERSION` recorded on the run.
- `temperature=0`, fixed seed where supported, schema-constrained output, explicit timeout.
- Untrusted content is passed in a clearly delimited data block; never concatenated into instructions.
- Never use LLM output to build SQL, shell commands, file paths, or URLs without validation.

## 6. Database & API

- Access the DB only through repository functions in `db/`. No SQL in business logic.
- Migrations only via Alembic; never edit applied migrations.
- FastAPI: one router per resource, request/response models explicit, no business logic in route handlers.

## 7. TypeScript (dashboard)

- `strict: true`. No `any`; use `unknown` and narrow.
- Function components + hooks. One component per file, `PascalCase.tsx`.
- Server data via a typed API client generated from the OpenAPI schema. No hand-written fetch types.
- Styling via design tokens only (see `DESIGN_SYSTEM.md`); no hard-coded colours or px values.

## 8. Git & review

- Branches: `feat/...`, `fix/...`, `chore/...`, `docs/...`.
- Conventional Commits: `feat(rank): add tie-break on seller_id`.
- PRs small (< ~400 lines changed), include: what/why, tests added, and any change to claims or limitations.
- A PR that changes benchmark scenarios, metrics, or thresholds must say so explicitly in the description (prevents quiet metric tuning).
- No force-push to `main`. Squash merge.

## 9. Dependencies

- Add dependencies sparingly; justify in the PR.
- Pin exact versions in `uv.lock` / `pnpm-lock.yaml`. Prefer releases at least two weeks old.
- Run `pip-audit` / `pnpm audit` in CI.

## 10. Do / Don't quick list

| Do | Don't |
|---|---|
| Inject clock, RNG, LLM client | Call `datetime.now()` or `random` directly in logic |
| Use `Decimal` for money | Use `float` for money |
| Fail closed with a reason code | Return `ALLOW` on error |
| Store hashes of raw content | Log raw page HTML |
| Record model + prompt version per run | Compare runs across unrecorded model changes |
| Report failures in the benchmark | Drop scenarios that make results look worse |
