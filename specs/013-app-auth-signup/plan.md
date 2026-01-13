# Implementation Plan: App Authentication and Signup Support

**Branch**: `013-app-auth-signup` | **Date**: 2025-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-app-auth-signup/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable the mobile crawler to handle apps requiring authentication by supporting email-based signup flows. The crawler will detect signup/login screens, switch to Gmail app to retrieve OTP codes or confirmation links, complete verification, and store credentials for future crawls. This allows crawling apps that require user accounts without manual intervention.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: PySide6 6.x, Appium Python Client, cryptography (Fernet), existing mobile_crawler modules  
**Storage**: SQLite via existing DatabaseManager and UserConfigStore  
**Testing**: pytest with pytest-qt for GUI testing  
**Target Platform**: Windows/Linux desktop (controlling Android devices via Appium)  
**Project Type**: Single Python project with GUI  
**Performance Goals**: Gmail email retrieval within 30 seconds; credential lookup < 100ms  
**Constraints**: Must handle app switching without losing crawler state; encrypted credential storage required  
**Scale/Scope**: Single-user desktop application; supports multiple apps with stored credentials per app package

## Constitution Check

*GATE: Constitution is a placeholder template - no specific constraints to check.*

✓ No constitution violations detected (template not customized)

## Project Structure

### Documentation (this feature)

```text
specs/013-app-auth-signup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (existing structure)

```text
src/mobile_crawler/
├── ui/
│   ├── widgets/
│   │   └── settings_panel.py       # MODIFY: Add test_email field
├── domain/
│   ├── auth_manager.py              # NEW: Authentication flow orchestration
│   ├── gmail_interaction.py         # NEW: Gmail app interaction and OTP extraction
│   └── credential_manager.py       # NEW: Credential storage and retrieval
├── infrastructure/
│   ├── app_switcher.py              # NEW: App switching utilities
│   └── database.py                  # MODIFY: Add app_credentials table schema
├── core/
│   └── crawler_loop.py              # MODIFY: Integrate auth detection and handling
└── config/
    └── config_manager.py            # MODIFY: Support test_email config

tests/
├── domain/
│   ├── test_auth_manager.py         # NEW: Test authentication flows
│   ├── test_gmail_interaction.py    # NEW: Test Gmail OTP extraction
│   └── test_credential_manager.py   # NEW: Test credential storage
├── infrastructure/
│   └── test_app_switcher.py         # NEW: Test app switching
└── integration/
    └── test_auth_flow.py             # NEW: End-to-end auth flow tests
```

**Structure Decision**: Use existing single-project structure. New modules added to domain/ for business logic and infrastructure/ for device automation. Settings panel extended with test email field. Database schema extended for credential storage.

## Complexity Tracking

No constitution violations - no complexity justification needed.

---

## Phase 0: Research

See [research.md](research.md) for detailed research findings.

### Key Research Areas

1. **App Switching with Appium**: How to reliably switch between target app and Gmail app
2. **Gmail OTP Extraction**: Methods for extracting OTP codes from Gmail emails using image-only approach
3. **Credential Storage Schema**: Database design for storing encrypted credentials per app package
4. **Authentication Detection**: How to detect signup/login screens using visual analysis

---

## Phase 1: Design & Contracts

See [data-model.md](data-model.md), [contracts/](contracts/), and [quickstart.md](quickstart.md) for detailed design artifacts.
