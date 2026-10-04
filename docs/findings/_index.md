---
author: claude
updated: 2026-10-04
---
# Findings log (for the Masterarbeit)

Observations about how real apps, devices and tools behave while crawling, recorded as they turn up so they can be cited later. One note per finding: `YYYY-MM-DD-<app-or-area>-<slug>.md`. Claude writes them (never `docs/notes/`); the evidence must come from a run, log or screenshot, and anything not verified is marked as such.

## Frontmatter

```yaml
author: claude
date: 2026-10-04
app: app.vera.prod            # package, or "none" for tool/device findings
runs: [216, 217]              # run ids that show it
category: anti-automation     # anti-automation | auth | ui-parsing | device | network | llm | crawler-limitation | other
status: confirmed             # confirmed | suspected | fixed-in-crawler | wont-fix
```

Body: **What we saw**, **Evidence** (run id, log line, file under the run folder), **Cause** (verified vs suspected), **Impact on the crawl**, **What the crawler does now**.

## Index

| Date | App | Category | Finding | Status |
|---|---|---|---|---|
| 2026-10-04 | app.vera.prod | anti-automation | [Black screenshots + misleading integrity screen](2026-10-04-app-vera-prod-blocks-screenshots.md) | confirmed |
