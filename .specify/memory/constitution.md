<!--
SYNC IMPACT REPORT
==================
Version Change: 0.0.0 → 1.0.1 (Initial Constitution + No Backward Compatibility Principle)

Modified Principles:
- N/A (Initial creation)

Added Sections:
- Core Principles (6 principles defined)
  - I. Test-Driven Development (NON-NEGOTIABLE)
  - II. Documentation-First
  - III. Image-Only Architecture
  - IV. Modular Design
  - V. Observability & Logging
  - VI. No Backward Compatibility (NEW)
- Development Workflow
- Quality Standards
- Governance

Removed Sections:
- N/A

Templates Requiring Updates:
- ✅ .specify/templates/plan-template.md - Updated Constitution Check with 6 principles including migration requirement
- ✅ .specify/templates/spec-template.md - Updated testing requirements
- ✅ .specify/templates/tasks-template.md - Updated to mandatory test-first approach

Follow-up TODOs:
- None

Rationale for Version 1.0.1:
- Initial constitution adoption with complete governance framework (1.0.0)
- Added Principle VI: No Backward Compatibility (MINOR version bump)
- This principle adds new guidance on data migration requirements
-->

# Mobile Crawler Constitution

## Core Principles

### I. Test-Driven Development (NON-NEGOTIABLE)

All new features and code changes MUST include comprehensive tests that are created and executed before implementation is considered complete. Tests serve as the primary validation mechanism and MUST pass before any code can be merged.

- Tests MUST be written for all new functionality
- Tests MUST be executed before code changes are committed
- Test failures MUST block code integration
- Coverage metrics MUST be tracked and maintained
- Both unit and integration tests are required for critical paths

**Rationale**: Tests provide the safety net that enables rapid iteration and prevents regressions. The test-first approach ensures requirements are understood before implementation and serves as living documentation of expected behavior.

### II. Documentation-First

All features, modules, and significant code changes MUST include top-level documentation that explains purpose, usage, and design decisions. Documentation is treated as a first-class deliverable alongside code.

- Every feature MUST have a specification document in specs/
- Public APIs MUST include docstrings with examples
- Complex algorithms MUST include explanatory comments
- Architecture decisions MUST be documented
- README and quickstart guides MUST be kept current

**Rationale**: Documentation ensures knowledge transfer, reduces onboarding time, and enables long-term maintainability. Without clear documentation, code becomes a liability rather than an asset.

### III. Image-Only Architecture

The crawler operates purely on visual feedback (screenshots) with coordinate-based actions. All implementations MUST respect this constraint and avoid XML/DOM access.

- All interactions MUST use screenshot-based analysis
- Actions MUST be coordinate-based, not element-based
- Text input MUST use ADB-based methods
- No XML page source or DOM hierarchy access
- AI providers MUST be configured for vision-only analysis

**Rationale**: Image-only mode provides platform independence and works across all Android apps without requiring accessibility services or XML parsing capabilities.

### IV. Modular Design

Code MUST be organized into self-contained, independently testable modules with clear interfaces and responsibilities.

- Each module MUST have a single, well-defined purpose
- Modules MUST be independently testable
- Clear boundaries between core, domain, infrastructure, and UI layers
- Dependency injection for external services
- No circular dependencies between modules

**Rationale**: Modular design enables parallel development, easier testing, and better maintainability. Clear boundaries prevent tight coupling and make the system more resilient to change.

### V. Observability & Logging

All operations MUST produce structured, searchable logs that enable debugging and monitoring of the crawler's behavior.

- Structured logging with consistent format
- All AI interactions MUST be logged (requests, responses, timing)
- Action execution MUST be logged with context
- Errors MUST include full stack traces and context
- Performance metrics MUST be captured and reported

**Rationale**: Comprehensive logging is essential for debugging AI-driven systems where behavior can be non-deterministic. Logs provide the audit trail needed to understand and improve crawler performance.

### VI. No Backward Compatibility

The project does not maintain backward compatibility for code changes. When code changes affect data structures or APIs, old data MUST be migrated to use the new code.

- No backward compatibility maintenance for code changes
- Data structure changes MUST include migration scripts
- Migration scripts MUST be tested before deployment
- Database schema changes MUST be versioned and documented
- API changes MUST be breaking changes with clear migration path
- Old data formats MUST be migrated to new formats on upgrade
- Migration failures MUST be detected and reported

**Rationale**: Maintaining backward compatibility adds significant complexity and technical debt. By requiring explicit data migration for changes, we ensure the codebase remains clean and maintainable. This approach forces intentional design decisions and prevents accumulation of legacy code paths.

## Development Workflow

### Feature Development Process

1. **Specification**: Create feature spec in specs/[###-feature-name]/spec.md with user stories, requirements, and acceptance criteria
2. **Planning**: Generate implementation plan with technical context and architecture decisions
3. **Testing**: Write tests FIRST, ensure they FAIL before implementation
4. **Implementation**: Write code to make tests pass
5. **Documentation**: Update top-level docs (README, quickstart, API docs)
6. **Validation**: Run full test suite, ensure all tests pass
7. **Review**: Code review with focus on test coverage and documentation completeness

### Code Review Checklist

- [ ] Tests exist and pass for all changes
- [ ] Documentation is updated (README, docstrings, specs)
- [ ] Code follows modular design principles
- [ ] Logging is comprehensive and structured
- [ ] Image-only architecture constraints are respected
- [ ] No regressions in existing functionality
- [ ] If data structures/APIs changed: migration scripts exist and are tested
- [ ] Old data migration plan documented and validated

## Quality Standards

### Testing Requirements

- **Unit Tests**: All functions and classes MUST have unit tests
- **Integration Tests**: Cross-module interactions MUST have integration tests
- **Contract Tests**: External service integrations MUST have contract tests
- **Coverage**: Minimum 80% code coverage for new code
- **Test Execution**: Full test suite MUST pass before merging

### Documentation Requirements

- **README**: Project overview, installation, usage examples MUST be current
- **Feature Specs**: All features MUST have specs/ documentation
- **API Docs**: Public interfaces MUST have docstrings with examples
- **Architecture Docs**: Complex systems MUST have design documentation
- **Changelog**: Significant changes MUST be documented

### Code Quality Standards

- **Linting**: Code MUST pass ruff linting with no errors
- **Formatting**: Code MUST be formatted with black
- **Type Hints**: All public functions MUST have type hints
- **Error Handling**: All errors MUST be caught and logged with context
- **Security**: API keys and secrets MUST be encrypted

### Data Migration Requirements

When code changes affect data structures or APIs:

- **Migration Scripts**: MUST be created for all data structure changes
- **Migration Testing**: Migration scripts MUST be tested with sample data before deployment
- **Schema Versioning**: Database schema changes MUST be versioned with clear documentation
- **Breaking Changes**: API changes MUST be documented as breaking with migration path
- **Data Validation**: Migrated data MUST be validated for integrity
- **Rollback Plan**: Migration MUST include rollback procedure in case of failure
- **Migration Logging**: All migration operations MUST be logged with success/failure status

## Governance

### Amendment Procedure

This constitution supersedes all other development practices. Amendments require:

1. Documentation of proposed changes with rationale
2. Review and approval from project maintainers
3. Migration plan for existing code and documentation
4. Version bump following semantic versioning rules
5. Update to all dependent templates and documentation

### Versioning Policy

Constitution versions follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Backward incompatible governance/principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- All pull requests MUST verify compliance with this constitution
- Complexity MUST be justified against principles
- Violations MUST be documented with rationale in commit messages
- Regular audits of code and documentation for compliance

### Runtime Guidance

For detailed development guidance, refer to:
- README.md for project overview and quickstart
- .specify/templates/ for specification and task templates
- Individual feature specs in specs/ for feature-specific requirements

**Version**: 1.0.1 | **Ratified**: 2026-01-13 | **Last Amended**: 2026-01-13
