# Contributing

## Setup

```bash
git clone <repo> && cd trade-iq
make setup
```

## Workflow

1. Branch from `dev`: `git checkout -b feat/description`
2. Small commits following Conventional Commits format
3. `make all` must be green before push (`lint` + `type-check` + `test`)
4. Open PR against `dev` (`main` is the stable line)
5. Wait for CI green + code review approval

## Commit types

`feat` | `fix` | `test` | `docs` | `chore` | `refactor` | `perf` | `ci` | `build` | `style` | `revert`

Enforced by `.githooks/commit-msg`. Run `make setup` to install the hook.

## Branch naming

| Prefix | Use for |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `chore/` | Maintenance |
| `refactor/` | Code restructure |
| `test/` | Test-only changes |
| `docs/` | Documentation |
| `ci/` | CI/CD changes |
| `hotfix/` | Urgent production fix |
| `release/` | Release preparation |

## Tests

Three tiers (see [docs/testing.md](docs/testing.md)):

- **Unit** — `make test` — fast, mocked, deterministic; coverage reported (80% target).
- **Integration** — `make integration` — runnable examples against the API endpoints.
- **Metrics (mass testing)** — `make evaluate` — mass model evaluation over the
  ground-truth dataset (`src/tests/data/intent_dataset.json`), scoring intent
  accuracy, groundedness, relevance and format; writes an HTML report.

## Code standards

The strictest toolchain, all pinned in `uv.lock` and enforced in CI:

- **black** — formatting; `make format` to apply, `black --check` must pass.
- **ruff** — linting; `make lint`.
- **ty** — static type checking; `make type-check`. Type annotations required.
- **pytest** — tests; `make test`.
- Secrets go in `.env` only — never hardcoded, never committed.
- Use `structlog` for logging — no bare `print()` calls.

`make all` (lint + type-check + test) must be green before pushing; local
pre-commit hooks mirror CI (black, ruff, ty).
