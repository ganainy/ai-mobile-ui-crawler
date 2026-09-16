# CLAUDE.md

## Codebase knowledge graph

This repo has a generated knowledge graph at `.ua/knowledge-graph.json`, produced by the `/understand` (Understand-Anything) tool. It maps every file, function, and class in the project along with their relationships (imports, calls, tests, etc.), grouped into architectural layers with a guided tour.

When you need to understand the project's architecture, find how components relate, or get oriented before making a change, read `.ua/knowledge-graph.json` (or use the `/understand-explain`, `/understand-chat`, or `/understand-dashboard` skills) instead of re-deriving the structure from scratch by grepping the whole tree.

- `.ua/knowledge-graph.json` — nodes, edges, layers, and tour. Check `.ua/meta.json`'s `gitCommitHash` to see how stale it is relative to `HEAD`.
- Re-run `/understand` after significant structural changes to keep it current.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues (`gh` CLI) in `ganainy/ai-mobile-ui-crawler`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/` at the repo root). See `docs/agents/domain.md`.
