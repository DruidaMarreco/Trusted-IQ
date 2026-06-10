---
name: release-workflow
description: Use this skill when the user asks to cut a release, bump version, tag, or update the CHANGELOG. Drives the end-to-end release process with SemVer, Conventional Commits, and git tagging.
---

# Release Workflow

Prepares and publishes a release using SemVer + Keep a Changelog + git tagging.

## When to use

- "Vamos fazer release"
- "Bump version"
- "Cria tag"
- "Update CHANGELOG"
- "Publish v1.2.0"

## Pre-flight (refuse if any fails)

1. **On `main` branch** with clean working tree: `git status && git rev-parse --abbrev-ref HEAD`.
2. **Up to date with origin**: `git fetch && git status` says "up to date".
3. **CI is green** on the latest commit: check via `gh run list -L 1 --branch main`.
4. **`[Unreleased]` section has entries** in `CHANGELOG.md`. If empty, refuse — nothing to release.

## Decide the version bump (SemVer)

Inspect the `[Unreleased]` entries:

| Trigger | Bump |
|---|---|
| Any `Removed` or `Changed` that breaks API | **MAJOR** |
| Any `Added` (new feature, retrocompatible) | **MINOR** |
| Only `Fixed`, `Security`, internal `Changed` | **PATCH** |

Ask the user to confirm if the decision is non-obvious.

## Steps

### 1. Update `CHANGELOG.md`

Move everything from `[Unreleased]` to a new `[X.Y.Z] - YYYY-MM-DD` section.
Leave `[Unreleased]` empty (keep the 6 category headers: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`).

Update comparison links at the bottom:

```markdown
[Unreleased]: https://github.com/org/repo/compare/vX.Y.Z...HEAD
[X.Y.Z]: https://github.com/org/repo/compare/vOLD...vX.Y.Z
```

**CHANGELOG category rules:**

| Category | What goes here |
|---|---|
| `Added` | New user-visible features |
| `Changed` | Changes to existing features |
| `Deprecated` | Soon-to-be removed features |
| `Removed` | Removed features |
| `Fixed` | Bug fixes |
| `Security` | Vulnerability fixes |

What does NOT go in CHANGELOG: `chore:` bumps, style fixes, internal refactors, test additions.

### 2. Bump version in `pyproject.toml`

Manually edit `[project] version`, or use:
```bash
uv run bump-my-version bump patch        # 1.0.0 → 1.0.1
uv run bump-my-version bump minor        # 1.0.0 → 1.1.0
uv run bump-my-version bump major        # 1.0.0 → 2.0.0
```

(If `bump-my-version` is not installed, `uv add --group dev bump-my-version` first.)

### 3. Generate CHANGELOG entries (optional, with `git-cliff`)

```bash
uv run git-cliff --unreleased --strip header   # preview
uv run git-cliff --output CHANGELOG.md         # write
```

Then review and clean the output — `git-cliff` is a starting point, not the final text.

### 4. Commit and tag

```bash
git add CHANGELOG.md pyproject.toml uv.lock
git commit -m "chore(release): vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### 5. Push

```bash
git push origin main
git push origin vX.Y.Z
```

### 6. Create GitHub Release

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z" \
  --notes-from-file <(awk '/^## \[X.Y.Z\]/,/^## \[/' CHANGELOG.md | head -n -1)
```

Or via UI: **Releases → Draft new release → Choose tag `vX.Y.Z` → paste CHANGELOG section**.

### 7. (Production apps) Trigger deploy

If a deploy workflow is gated on `tag push`, it should now run. Monitor:
```bash
gh run watch
```

### 8. (Optional) Supply-chain artefacts

For releases shipping container images:
```bash
docker build -t <registry>/<app>:vX.Y.Z .
trivy image <registry>/<app>:vX.Y.Z          # scan, must pass
cosign sign --key cosign.key <registry>/<app>:vX.Y.Z
cyclonedx-py environment --output-file sbom-vX.Y.Z.json
gh release upload vX.Y.Z sbom-vX.Y.Z.json
```

## Rollback procedure

If a release is broken **after** tagging:

1. **Do not delete the tag** — it's immutable history.
2. Create a `fix:` PR, merge, and immediately cut a new patch release (`vX.Y.Z+1`).
3. Mark the broken release in `CHANGELOG.md` with a `> ⚠️ Broken release — superseded by vX.Y.Z+1` note.
4. For container images, retag `:latest` to the previous good version.

## Forbidden

- Force-pushing over a release tag.
- Skipping the CHANGELOG update — "we'll add it later" never happens.
- Releasing from a branch other than `main`.
- Releasing with red CI.
- Bumping MAJOR without a documented migration guide for consumers.
