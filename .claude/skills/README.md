# Engineering Skills — Claude Code

Conjunto de skills que automatizam a montagem e gestão de repositórios Python profissionais.
Cada skill é **auto-contida** — sem dependências externas ou referências a ficheiros fora da pasta `skills/`.

## Como o Claude Code descobre estas skills

Cada subpasta tem um `SKILL.md` com frontmatter YAML (`name` + `description`). O Claude lê a descrição e invoca a skill automaticamente quando o pedido do utilizador corresponde — não é preciso referir o nome explicitamente, mas podes (`"usa a skill scaffold-python-repo"`).

## Setup (executar uma vez por repositório)

| Skill | Fase do Quickstart | Quando invocar |
|---|---|---|
| `scaffold-python-repo` | 1 + 2 | "novo projecto Python", "scaffold", "bootstrap" |
| `scaffold-tests` | 3 | "configurar testes", "pytest setup" |
| `scaffold-ci-cd` | 4 | "GitHub Actions", "configurar CI", "Dependabot" |
| `scaffold-docker` | 5 | "Dockerfile", "containerizar", "docker-compose" |
| `scaffold-observability` | 6 | "logging", "settings", "Sentry", "OpenTelemetry" |
| `scaffold-docs-governance` | 7 | "README", "CONTRIBUTING", "ADR", "SECURITY.md" |

## Gestão (executar repetidamente)

| Skill | Quando invocar |
|---|---|
| `manage-dependencies` | "adicionar dep", "remover lib", "upgrade", "audit" |
| `release-workflow` | "release", "bump version", "tag", "CHANGELOG" |
| `audit-repo-health` | "audita o repo", "verifica conformidade", "health check" |

## Ordem recomendada para novo repo

```
1. scaffold-python-repo
2. scaffold-tests
3. scaffold-ci-cd
4. scaffold-docker         (se for aplicação)
5. scaffold-observability  (se for app com lógica de negócio)
6. scaffold-docs-governance
7. audit-repo-health       (confirmar tudo OK)
```

## Instalação a nível de utilizador (todas as máquinas)

```bash
mkdir -p ~/.claude/skills
cp -r .claude/skills/* ~/.claude/skills/
```

Project-level skills (`.claude/skills/`) têm prioridade sobre user-level se houver conflito de nome.
