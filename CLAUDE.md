# CLAUDE.md

## Codebase knowledge graph

This repo has a generated knowledge graph at `.ua/knowledge-graph.json`, produced by the `/understand` (Understand-Anything) tool. It maps every file, function, and class in the project along with their relationships (imports, calls, tests, etc.), grouped into architectural layers with a guided tour.

When you need to understand the project's architecture, find how components relate, or get oriented before making a change, read `.ua/knowledge-graph.json` (or use the `/understand-explain`, `/understand-chat`, or `/understand-dashboard` skills) instead of re-deriving the structure from scratch by grepping the whole tree.

- `.ua/knowledge-graph.json` — nodes, edges, layers, and tour. Check `.ua/meta.json`'s `gitCommitHash` to see how stale it is relative to `HEAD`.
- Re-run `/understand` after significant structural changes to keep it current.
