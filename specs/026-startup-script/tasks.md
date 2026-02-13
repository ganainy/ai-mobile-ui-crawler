# Tasks: Application Startup Script

**Input**: Design documents from `/specs/026-startup-script/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md  
**Tests**: Manual verification only (no automated tests required per spec)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Script location**: `scripts/start.ps1` at repository root
- **Existing files**: `run_ui.py` (unchanged)

---

## Phase 1: Setup

**Purpose**: Create project structure for the startup script

- [x] T001 Create `scripts/` directory at repository root
- [x] T002 Create empty `scripts/start.ps1` with script boilerplate (CmdletBinding, param block, script header)

---

## Phase 2: User Story 1 & 2 - One-Command Launch with Dependency Detection (Priority: P1) 🎯 MVP

**Goal**: Launch the complete application stack (MobSF, Appium, UI) with a single command, with warnings for missing dependencies

**Independent Test**: Run `.\scripts\start.ps1` and verify all three components start. Verify warnings appear if Docker/npm are missing.

### Helper Functions

- [x] T003 [P] [US1] Implement `Write-Status` function for colored console output in `scripts/start.ps1`
- [x] T004 [P] [US2] Implement `Test-CommandExists` function to check if a command is in PATH in `scripts/start.ps1`
- [x] T005 [P] [US2] Implement `Test-DockerRunning` function to check if Docker daemon is running in `scripts/start.ps1`
- [x] T006 [P] [US2] Implement `Test-PortInUse` function to check if a port is already occupied in `scripts/start.ps1`

### Dependency Detection (US2)

- [x] T007 [US2] Implement `Test-Dependencies` function that checks Docker, npm/npx, and Python availability in `scripts/start.ps1`
- [x] T008 [US2] Add warning messages with installation URLs when dependencies are missing in `scripts/start.ps1`

### Component Startup (US1)

- [x] T009 [US1] Implement `Start-MobSF` function to launch Docker container on port 8000 in `scripts/start.ps1`
- [x] T010 [US1] Implement `Start-Appium` function to launch Appium server on port 4723 in `scripts/start.ps1`
- [x] T011 [US1] Implement `Start-MainUI` function to launch `python run_ui.py` in `scripts/start.ps1`
- [x] T012 [US1] Implement `Wait-ForService` function with port polling and timeout in `scripts/start.ps1`

### Main Execution Flow (US1)

- [x] T013 [US1] Implement main execution flow: check deps → start MobSF → start Appium → wait for ready → start UI in `scripts/start.ps1`
- [x] T014 [US1] Add status messages showing progress of each startup step in `scripts/start.ps1`

**Checkpoint**: ✅ COMPLETE - Running `.\scripts\start.ps1` starts all components with dependency warnings.

---

## Phase 3: User Story 3 - Process Management (Priority: P2)

**Goal**: Gracefully handle Ctrl+C shutdown and process cleanup

**Independent Test**: Start the script, press Ctrl+C, verify all processes (Docker container, Appium) are stopped cleanly.

### Implementation

- [x] T015 [US3] Add `$script:StartedProcesses` array to track launched processes in `scripts/start.ps1`
- [x] T016 [US3] Implement `Stop-AllProcesses` function to terminate tracked processes in `scripts/start.ps1`
- [x] T017 [US3] Implement `Stop-MobSFContainer` function using `docker stop` for clean container shutdown in `scripts/start.ps1`
- [x] T018 [US3] Wrap main execution in `try/finally` block to call cleanup on Ctrl+C in `scripts/start.ps1`
- [x] T019 [US3] Add port-in-use detection before starting each component (skip if already running) in `scripts/start.ps1`

**Checkpoint**: ✅ COMPLETE - Script handles Ctrl+C gracefully and cleans up all processes.

---

## Phase 4: User Story 4 - Optional Component Startup (Priority: P3)

**Goal**: Allow users to skip specific components via command-line flags

**Independent Test**: Run `.\scripts\start.ps1 -NoMobsf` and verify only Appium and UI start.

### Implementation

- [x] T020 [US4] Add `-NoMobsf` switch parameter to skip MobSF startup in `scripts/start.ps1`
- [x] T021 [US4] Add `-NoAppium` switch parameter to skip Appium startup in `scripts/start.ps1`
- [x] T022 [US4] Add `-UiOnly` switch parameter that implies both -NoMobsf and -NoAppium in `scripts/start.ps1`
- [x] T023 [US4] Add `-Help` switch parameter with usage documentation in `scripts/start.ps1`
- [x] T024 [US4] Update main execution flow to respect skip flags in `scripts/start.ps1`

**Checkpoint**: All optional flags work correctly.

---

## Phase 5: Polish & Documentation

**Purpose**: Final cleanup and documentation

- [x] T025 [P] Update `README.md` with startup script usage instructions
- [x] T026 [P] Verify `specs/026-startup-script/quickstart.md` matches final implementation
- [ ] T027 Run full manual test: start all components, use the app, Ctrl+C to stop
- [ ] T028 Run manual test: verify warnings appear correctly when Docker/npm are unavailable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 & 2 (Phase 2)**: Depends on Setup - This is the MVP
- **User Story 3 (Phase 3)**: Depends on Phase 2 (needs processes to manage)
- **User Story 4 (Phase 4)**: Depends on Phase 2 (needs component functions to skip)
- **Polish (Phase 5)**: Depends on all user stories being complete

### Task Dependencies Within Phases

**Phase 2 (US1 & US2):**
- T003-T006 (helper functions) can all run in **parallel**
- T007-T008 depend on T004, T005 (uses helper functions)
- T009-T012 (component functions) can run in **parallel** after T003, T006
- T013-T014 depend on T007-T012 (orchestrates all functions)

**Phase 3 (US3):**
- T015-T017 can run in **parallel**
- T018 depends on T015-T017 (uses cleanup functions)
- T019 depends on T006 (uses port check function)

**Phase 4 (US4):**
- T020-T023 can all run in **parallel** (each adds a parameter)
- T024 depends on T020-T023 (uses all parameters)

### Parallel Opportunities

```text
# Phase 2 - Helper functions (can run in parallel):
T003: Write-Status function
T004: Test-CommandExists function
T005: Test-DockerRunning function
T006: Test-PortInUse function

# Phase 2 - Component functions (can run in parallel after helpers):
T009: Start-MobSF function
T010: Start-Appium function
T011: Start-MainUI function
T012: Wait-ForService function

# Phase 4 - Parameters (can run in parallel):
T020: -NoMobsf parameter
T021: -NoAppium parameter
T022: -UiOnly parameter
T023: -Help parameter
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: US1 & US2 (T003-T014)
3. **STOP and VALIDATE**: Test full startup with `.\scripts\start.ps1`
4. Script is now usable for daily development!

### Incremental Delivery

1. **MVP**: Setup + US1/US2 → Single-command startup works
2. **Add US3**: Process management → Clean Ctrl+C shutdown
3. **Add US4**: Optional flags → Full flexibility
4. **Polish**: Documentation → Production ready

---

## Summary

| Phase | User Story | Tasks | Parallel Tasks |
|-------|------------|-------|----------------|
| 1 | Setup | 2 | 0 |
| 2 | US1 & US2 (P1) | 12 | 8 |
| 3 | US3 (P2) | 5 | 3 |
| 4 | US4 (P3) | 5 | 4 |
| 5 | Polish | 4 | 2 |
| **Total** | | **28** | **17** |

**Suggested MVP Scope**: Complete through Phase 2 (Tasks T001-T014) for a fully functional startup script.

---

## Notes

- All tasks modify a single file (`scripts/start.ps1`) but target different functions
- [P] tasks modify different functions with no dependencies
- Manual testing only - no automated test suite required
- Script uses PowerShell 5.1+ features available on all Windows 10/11 systems
