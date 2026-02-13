<!-- Pull Request Template
Use this template to make PRs reviewable and to ensure checks required by our SPECKIT principles are visible.
-->

## Summary
What does this change do? Why is it needed? Include any screenshots or short recordings for UI changes.

## Implementation notes
Short notes about design decisions, public API changes, or notable trade-offs.

## Checklist (required)
- [ ] Title and description explain what, why, and impact on UX/performance.
- [ ] Change is small and focused OR split into reviewable commits/PRs.
- [ ] Public APIs have docstrings/type hints and minimal surface area.
- [ ] Unit tests added/updated (happy path + edge cases).
- [ ] Integration tests added/updated for external interactions (if applicable).
- [ ] Linting and type checks pass locally; CI passes.
- [ ] Performance statement included for performance-sensitive changes (baseline and expected).
- [ ] UX notes/screenshots included for UI changes.
- [ ] Migration or rollback notes provided for breaking changes.
- [ ] All open questions answered or noted for follow-up.

## Link to principles
Please read and follow our engineering principles: `.github/prompts/speckit.principles.md`.

<!-- Optional: add checklist items specific to your change below -->

## Testing notes
How to run tests for this change locally, fixture setup (if any), and expected results.

## Related issues
Refs: 
