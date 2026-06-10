# Contributing

## Setup

```bash
git clone <repo> && cd trade-iq-pod
make setup
```

## Workflow

1. Branch from `main`: `git checkout -b feat/description`
2. Small commits following Conventional Commits format
3. `make all` must be green before push (`lint` + `type-check` + `test`)
4. Open PR against `main`
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

- Unit: `make test` (coverage threshold: 80%)
- Integration: `make test-integration` (requires external services)

## Code standards

- Type annotations required — `mypy --strict` must pass
- Linting via `ruff` — run `make lint` and `make format`
- Secrets go in `.env` only — never hardcoded, never committed
- Use `structlog` for logging — no bare `print()` calls
