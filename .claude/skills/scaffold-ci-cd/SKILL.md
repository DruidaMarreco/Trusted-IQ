---
name: scaffold-ci-cd
description: Use this skill when the user asks to configure CI/CD with GitHub Actions, Dependabot, branch protection, or release automation for a Python project. Covers Phase 4 of the engineering Quickstart.
---

# Scaffold CI/CD (Fase 4)

Creates `.github/workflows/ci.yml`, `dependabot.yml`, PR template, CODEOWNERS, and documents branch protection setup.

## When to use

- "Configurar GitHub Actions"
- "Setup CI"
- "Dependabot"
- "Branch protection"

## Pre-conditions

- Repo already pushed to GitHub.
- `Makefile`, `pyproject.toml`, and tests exist.

## Steps

### 1. `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --group dev --frozen

      - name: Lint
        run: uv run ruff check .

      - name: Format check
        run: uv run ruff format --check .

      - name: Type check
        run: uv run mypy .

      - name: Unused deps
        run: uv run deptry .

      - name: Unit tests with coverage
        run: uv run pytest tests/unit --cov --cov-report=xml --cov-fail-under=80

      - name: Security audit
        run: uv run pip-audit

      - name: Secret scanning
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  integration:
    runs-on: ubuntu-latest
    needs: quality
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv python install 3.12
      - run: uv sync --group dev --frozen
      - run: uv run pytest tests/integration -m integration
        env:
          API_KEY: ${{ secrets.API_KEY }}
```

**Key rules:**
- `permissions: contents: read` — least privilege.
- `uv sync --frozen` — fails if lockfile is out of sync.
- Pin actions with SHA in security-sensitive repos (not tags).

### 2. `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    groups:
      dev-dependencies:
        dependency-type: "development"
      production-dependencies:
        dependency-type: "production"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "docker"   # remove if no Dockerfile
    directory: "/"
    schedule:
      interval: "weekly"
```

Grouped updates avoid 30 individual PRs per week.

### 3. `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Descrição

Breve descrição do que esta PR faz.

## Tipo de alteração

- [ ] feat: nova funcionalidade
- [ ] fix: correção de bug
- [ ] refactor: refactoring
- [ ] test: testes
- [ ] docs: documentação
- [ ] chore: manutenção

## Checklist

- [ ] O código segue as convenções do projecto
- [ ] Self-review feito
- [ ] Testes adicionados/actualizados
- [ ] Documentação actualizada (se aplicável)
- [ ] CI passa sem erros
- [ ] Sem secrets ou dados sensíveis commitados
```

### 4. `.github/CODEOWNERS`

```
* @<owner-or-team>
/.github/ @<owner-or-team>
/docs/ @<owner-or-team>
```

Ask the user for the owner/team handle.

### 5. `.github/ISSUE_TEMPLATE/` (optional but recommended)

- `bug_report.md`
- `feature_request.md`

### 6. Branch protection (GitHub UI or `gh` CLI)

Cannot be done via files. Provide the user with the **exact gh CLI command**:

```bash
gh api -X PUT "repos/<owner>/<repo>/branches/main/protection" \
  -f required_status_checks.strict=true \
  -f required_status_checks.contexts[]='quality' \
  -f enforce_admins=true \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f restrictions= \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

Or document the UI path: **Settings → Branches → Add rule → `main`** with: require PR review (1), require status checks (`quality`), require branches up to date, no force pushes, no deletions.

### 7. Hardening (advanced, ask the user)

- Pin GitHub Actions with **SHA** instead of tags (`actions/checkout@8ade135...  # v4`). Tool: [pinact](https://github.com/suzuki-shunsuke/pinact).
- Add `gitleaks-action` + secret scanning alerts.

### 8. Commit & verify

```bash
git add .github/
git commit -m "ci: add CI workflow, dependabot, PR template, CODEOWNERS"
git push
```

Wait for the first CI run. Investigate and fix any red checks before declaring done.

## Hand-off

Recommend `scaffold-docker` (if app) or `scaffold-docs-governance` (if library).
