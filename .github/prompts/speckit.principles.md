## SPECKIT Engineering Principles

Purpose: A concise, practical set of principles for contributors and reviewers to ensure code is clean, non-fragile, expandable, well-tested, UX-consistent, and performance-explicit. Follow these in design, implementation, reviews, and CI automation.

---

### Contract (2–4 bullets)
- Inputs: code changes (PRs), design proposals, UX flows; outputs: maintainable code, tests, documentation, measurable performance statements and UX notes.
- Data shapes: functions and modules must declare input/output types (docstrings, type hints, or interface files) and error modes.
- Success criteria: code is readable, covered by tests, passes CI, meets stated performance targets, and preserves or improves UX consistency.
- Error modes: functions fail fast with clear errors; public APIs document expected exceptions and recovery strategies.

### Core Principles
1. Clean & Explicit Code
   - Prefer small, single-responsibility functions and modules. Keep public APIs minimal and well-documented.
   - Use descriptive names; avoid cleverness. Each module should include a short top-level docstring describing purpose, inputs, outputs, and side effects.
   - Make intent explicit: prefer explicit over implicit control flow, and return results instead of mutating global state where possible.

2. Non-fragile (Robustness)
   - Validate inputs at boundaries with clear, informative errors. Use guards for preconditions and assert invariants in dev builds.
   - Avoid brittle coupling: prefer interfaces/abstractions and dependency injection for external systems (DB, devices, services).
   - Fail gracefully where possible; if unrecoverable, log context and bubble a clear error to calling layers.

3. Expandable & Modular
   - Design modules for extension: use small, well-defined interfaces so new behavior can be added without touching existing code.
   - Keep configuration and feature flags centralized; document how to add new capabilities and how they affect dependencies.
   - Maintain backwards compatibility for public interfaces; if breaking change is necessary, document migration steps and bump versioning appropriately.

4. Strict Testing
   - Every new feature must include unit tests (happy path + edge cases) and integration tests when interacting with external systems.
   - Tests must be deterministic, fast, and isolated. Use fixtures, mocks, or test doubles for external dependencies.
   - Add at least one regression test for each discovered bug. Aim for meaningful coverage, not a coverage number alone.
   - CI gates: PRs must pass linting, type checks (if applicable), unit tests, and integration tests where relevant before merge.

5. Consistent UX
   - Follow established UI patterns (components, naming, flows). Keep interactions predictable and consistent across screens and components.
   - Document UX decisions in PRs for significant flows or deviating patterns (why the change improves user experience).
   - Accessibility and internationalization: include basic accessibility checks and ensure text is localizable when applicable.

6. Explicit Performance
   - State performance expectations for non-trivial code paths (latency, memory, CPU). For example: "Endpoint X should respond <200ms under Y load" or "Memory overhead should not exceed Z MB per worker." 
   - Measure before and after: include a short local benchmark or metrics capture in PRs that touch performance-sensitive paths.
   - For high-cost operations, provide non-blocking alternatives (async, batching, caching) and document trade-offs.

7. Ask Early, Ask Often
   - If any requirement, interface, or expected behavior is unclear, stop and ask the author/owner or the user. Document the question and the accepted answer in the PR.
   - Use short clarifying questions in PR comments or an issue when the change affects expectations, UX, or performance.

---

### PR Review Checklist (use on every PR)
- [ ] Title and description explain what, why, and impact on UX/performance.
- [ ] Small, focused change set; if large, broken into reviewable steps.
- [ ] Code includes docstrings/type hints for public functions/classes.
- [ ] Tests: unit tests added/updated (happy + edge cases). Integration tests for external interactions.
- [ ] Lint and type checks pass locally; CI passes.
- [ ] Performance: statement of performance expectations and a brief benchmark or reasoning if relevant.
- [ ] UX: list of screens/components affected and screenshots/recording when UI changes are present.
- [ ] Migration notes for breaking changes and an explicit rollback plan if risky.
- [ ] All open questions answered or explicitly flagged for follow-up.

### Testing Requirements (practical rules)
- Unit tests should cover core logic and edge cases. Aim for fast (<100ms per test file) tests where possible.
- Integration tests should run in CI for components interacting with external services; use recorded fixtures or short-lived containers when possible.
- End-to-end tests reserved for critical flows; keep them few and resilient.
- Use test naming conventions and place tests next to the code under test when practical.

### Performance Guidance (how to be explicit)
- Document measurable targets in code comments/PR description and include a simple benchmarking snippet or metrics showing baseline.
- For caching/batching decisions, include expected invalidation strategy and memory/consistency trade-offs.
- If a change increases resource use, provide the reason, expected scale, and mitigation strategy.

### UX Consistency Rules
- Reuse existing components rather than creating new ones for similar patterns.
- Keep copy, labels, and iconography consistent. Use shared constants/files for repeated strings where localization is needed.
- For any UI change, include a short note on the reasoning and a screenshot/GIF for reviewers.

### When to Ask the User (concrete triggers)
- Ambiguous requirements or acceptance criteria.
- Changes that affect UX flows, wording, or behavior visible to users.
- Performance targets are not specified but are likely relevant to user-facing latency or scale.
- Any change that could be a breaking API or requires migration steps.

### Low-risk Proactive Extras (encouraged)
- Add or update a small example snippet or a test harness demonstrating intended use for a public API.
- Add a short performance script under `tools/benchmarks` if performance-sensitive code was changed.
- Add an automated checklist entry for CI (lint/tests) if a new language/tool is introduced.

---

## Notes & Next Steps
- Use this file as a living reference. Link it from `CONTRIBUTING.md` and code review templates.
- Suggested follow-ups: add CI enforcement for some checklist items (lint, tests), and add a PR template that prompts for performance and UX notes.

If anything here is unclear or you'd like a different tone (short checklist only, or expanded examples per language), tell me which format you prefer and I will update the document.
