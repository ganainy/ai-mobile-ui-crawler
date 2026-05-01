# Mobile UI Crawler

## What This Is

Mobile UI Crawler is a desktop-controlled Android app exploration system for internal developer use. It observes app screens, uses AI (with OmniParser-assisted UI understanding) to choose the next action, and executes actions on-device via ADB/Appium flows. Each run persists rich session data for later analysis and reporting.

## Core Value

Maximize reliable discovery of unique app screens and states while preserving resumable run history for analysis.

## Requirements

### Validated

- ✓ UI-driven crawl execution and monitoring via desktop app/CLI — existing
- ✓ AI-guided visual exploration loop with screenshot-based decisioning — existing
- ✓ Persistent run/session storage for actions, screens, and interactions — existing
- ✓ Post-run report generation from saved crawl artifacts — existing

### Active

- [ ] Increase unique screen/state discovery efficiency across long crawl sessions
- [ ] Improve run stability and resumability over raw crawl speed
- [ ] Tighten OmniParser-assisted element grounding quality for action planning
- [ ] Strengthen report quality for exploration coverage and state transition insights

### Out of Scope

- Fully autonomous account/login bypass and CAPTCHA solving — excluded for safety/reliability and non-core value
- Cloud multi-device orchestration — deferred; current target is single internal operator workflow

## Current Milestone: v1.0 Crawl Stability & Resumability

**Goal:** Make the crawler reliably survive crashes, handle errors properly, and resume from where it left off.

**Target features:**
- Durable run state — atomic step state machine, idempotent checkpoints, crash recovery
- Error model overhaul — typed exceptions, structured logging, fail-closed on critical paths
- UI sync hardening — explicit waits, post-action verification, adaptive backoff
- Context guardrails — native/webview drift handling, context normalization before actions

## Context

- Existing brownfield Python codebase with GUI (`PySide6`) + CLI (`Click`) and layered modules under `src/mobile_crawler/`.
- Traversal and action logic integrates with DroidRun (`external/droidrun`) and provider adapters under `src/mobile_crawler/domain/providers/`.
- Runtime and persistence context from mapped docs:
  - `\.planning\codebase\STACK.md`
  - `\.planning\codebase\ARCHITECTURE.md`
- Run/session data is persisted in SQLite and session directories, then consumed by report generation components.

## Constraints

- **Primary quality**: Stability and resumability over throughput — prioritized by project goal.
- **Platform**: Android app crawling with local desktop orchestration — depends on ADB/Appium availability.
- **Audience**: Internal developer workflow first — optimize for control/diagnostics over end-user polish.
- **Architecture**: Preserve existing UI + orchestration + persistence layering — reduce regression risk in a mature brownfield codebase.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Optimize for unique screen/state discovery as primary metric | Matches explicit project success definition | — Pending |
| Keep v1 focused on internal developer use | Reduces scope and accelerates reliability improvements | — Pending |
| Prioritize stability/resume over maximum speed | Long-running crawls are more valuable when recoverable | — Pending |
| Exclude autonomous login/CAPTCHA bypass from scope | Avoids fragile/high-risk automation and keeps focus on exploration core | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-01 after milestone v1.0 definition*
