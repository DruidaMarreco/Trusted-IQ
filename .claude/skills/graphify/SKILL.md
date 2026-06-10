---
name: graphify
description: Use this skill to build, query, or explore a knowledge graph of the current project using graphify. Auto-run when graphify-out/ is missing. Use for onboarding a new project, understanding codebase structure, querying relationships between files/functions, or tracing paths between components.
---

# Graphify — Knowledge Graph Skill

Converts project into interactive knowledge graph. Use for onboarding, codebase exploration, querying relationships, tracing paths.

## Auto-run rule

**On every project session start:** check if `graphify-out/` exists in project root.
- Missing → install graphify (if needed) + run `graphify .` before other work
- Present → skip build, graph available for queries

## Install check

```bash
# Check installed
graphify --version 2>/dev/null || pip install graphifyy && graphify install
```

## Commands

### Build graph
```bash
graphify .
```
Outputs to `graphify-out/`:
- `graph.html` — interactive visualization (open in browser)
- `GRAPH_REPORT.md` — core nodes, surprises, suggested questions
- `graph.json` — queryable graph
- `cache/` — incremental cache (subsequent runs faster)

### Query graph
```bash
graphify query "<question about codebase>"
```
Examples:
- `graphify query "what calls the auth module"`
- `graphify query "where is database config defined"`

### Trace path between components
```bash
graphify path <node-a> <node-b>
```

### Explain a node
```bash
graphify explain <file-or-function>
```

## When to use

| Trigger | Action |
|---|---|
| `graphify-out/` missing | auto-build on session start |
| "mapa do projeto" / "knowledge graph" / "explora o repo" | build or show existing |
| "como X está ligado a Y" / "o que usa Z" | `graphify query` |
| "caminho entre A e B" | `graphify path` |
| "explica este ficheiro/função" | `graphify explain` |
| Project onboarding | build graph, show `GRAPH_REPORT.md` summary |

## Output after build

1. Confirm `graphify-out/` created
2. Show summary from `GRAPH_REPORT.md` (core nodes + surprises sections)
3. Suggest 2-3 queries based on project structure

## Notes

- Requires Python 3.10+
- Processes `.py`, `.js`, `.go`, `.java`, Markdown, PDFs — no raw source sent to external APIs
- Incremental: re-run fast after first build (uses cache/)
- `graphify-out/` should be added to `.gitignore` (large HTML/JSON artifacts)
