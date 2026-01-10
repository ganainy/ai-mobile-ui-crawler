<!--
Sync Impact Report
==================
- Version change: 0.0.0 → 1.0.0 (initial ratification)
- Added Principles: I. Virtual Environment Isolation, II. Documentation Sync, III. Test-Driven Development, IV. Code Quality Gates
- Added Sections: Environment Setup, Development Workflow
- Templates requiring updates: ⚠ pending (tasks.md file paths reference src/ structure)
- Follow-up TODOs: None
-->

# Mobile Crawler Constitution

## Core Principles

### I. Virtual Environment Isolation (NON-NEGOTIABLE)
All development and execution MUST occur within a Python virtual environment (venv).
- NEVER install packages globally or to the system Python
- The project venv MUST be created at `.venv/` in the project root
- All terminal commands MUST activate the venv before execution
- Dependencies are managed exclusively via `pip install -e .` (editable mode) within the venv
- Rationale: Prevents dependency conflicts, ensures reproducible builds, isolates project from system Python

### II. Documentation Sync (NON-NEGOTIABLE)
Markdown documentation MUST be updated after every code change.
- README.md MUST reflect current project state (features, installation, usage)
- Docstrings MUST be present for all public modules, classes, and functions
- `specs/master/spec.md` is the source of truth for requirements
- Implementation plan (`specs/master/plan.md`) and tasks (`specs/master/tasks.md`) MUST be updated when scope changes
- Rationale: Documentation drift causes confusion; keeping docs current ensures onboarding efficiency and reduces ramp-up time

### III. Test-Driven Development (NON-NEGOTIABLE)
Tests MUST be run after every code change.
- `pytest` MUST pass before any change is considered complete
- New functionality requires corresponding unit tests (≥80% coverage target)
- Integration tests required for: database operations, Appium interactions, AI provider calls
- Test command: `pytest -v --cov=mobile_crawler`
- Rationale: Catching regressions immediately prevents cascading failures

### IV. Code Quality Gates
All code MUST pass linting and formatting checks.
- `ruff check .` MUST pass with no errors
- `black --check .` MUST pass (or use `ruff format`)
- Pre-commit hooks enforce these checks automatically
- Rationale: Consistent code style improves readability and reduces review friction

## Environment Setup

### Required Tools
| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥3.9 | Runtime |
| pip | Latest | Package management |
| venv | Built-in | Virtual environment |
| Appium | 2.x | Device automation |
| ADB | Latest | Android debugging |

### Virtual Environment Commands
```bash
# Create venv (one-time)
python -m venv .venv

# Activate venv (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate venv (Windows cmd)
.\.venv\Scripts\activate.bat

# Activate venv (Unix/macOS)
source .venv/bin/activate

# Install project in editable mode
pip install -e .

# Install dev dependencies
pip install pytest pytest-cov ruff black pre-commit
```

## Development Workflow

### After Every Code Change
1. **Run tests**: `pytest -v`
2. **Run linter**: `ruff check . --fix`
3. **Update docs**: If behavior changed, update relevant `.md` files
4. **Commit**: Include test results confirmation in commit message

### Before Starting New Feature
1. Check implementation plan in `.github/prompts/speckit.implementation-plan.md`
2. Verify task breakdown in `.github/prompts/speckit.tasks.md`
3. Ensure venv is activated
4. Run existing tests to confirm baseline

## Governance

This constitution supersedes all other development practices for the Mobile Crawler project.

- **Amendments**: Require documented rationale, version bump, and updated Last Amended date
- **Compliance**: All code contributions MUST adhere to these principles
- **Exceptions**: NONE for principles marked NON-NEGOTIABLE

**Version**: 1.0.0 | **Ratified**: 2026-01-10 | **Last Amended**: 2026-01-10
