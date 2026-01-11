# Tasks: Fix Settings Persistence

**Input**: Design documents from `/specs/001-fix-settings-persistence/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Not explicitly requested - included only for critical persistence verification.

**Organization**: Tasks grouped by user story (P1 → P2) for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project setup needed - using existing infrastructure

- [X] T001 Verify existing tests pass by running `pytest tests/ui/` in terminal
- [X] T002 [P] Verify UserConfigStore works by checking database creation in src/mobile_crawler/infrastructure/user_config_store.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify existing SettingsPanel persistence works correctly (FR-001, FR-002, FR-009)

**⚠️ CRITICAL**: User Story 1 (SettingsPanel) must be verified working before selector stories begin

- [X] T003 Verify SettingsPanel._load_settings() loads all values on startup in src/mobile_crawler/ui/widgets/settings_panel.py
- [X] T004 Verify SettingsPanel._on_save_clicked() persists all values to database in src/mobile_crawler/ui/widgets/settings_panel.py
- [X] T005 Verify API keys are encrypted via get_secret_plaintext/set_secret_plaintext in src/mobile_crawler/infrastructure/user_config_store.py

**Checkpoint**: SettingsPanel persistence verified - selector widget work can begin

---

## Phase 3: User Story 1 - Settings Panel Values Persist (Priority: P1) 🎯 MVP

**Goal**: Ensure Settings panel values (API keys, system prompt, crawl limits, credentials) persist across app restarts

**Independent Test**: Enter values → Save → Restart app → Verify all values restored

### Implementation for User Story 1

- [X] T006 [US1] Add test for settings persistence on app restart in tests/ui/test_settings_panel.py
- [X] T007 [US1] Verify existing _load_settings() correctly restores gemini_api_key in src/mobile_crawler/ui/widgets/settings_panel.py
- [X] T008 [US1] Verify existing _load_settings() correctly restores openrouter_api_key in src/mobile_crawler/ui/widgets/settings_panel.py
- [X] T009 [US1] Verify existing _load_settings() correctly restores system_prompt in src/mobile_crawler/ui/widgets/settings_panel.py
- [X] T010 [US1] Verify existing _load_settings() correctly restores max_steps and max_duration_seconds in src/mobile_crawler/ui/widgets/settings_panel.py
- [X] T011 [US1] Verify existing _load_settings() correctly restores test_username and test_password in src/mobile_crawler/ui/widgets/settings_panel.py

**Checkpoint**: User Story 1 (Settings Panel) is fully functional - this is the MVP

---

## Phase 4: User Story 2 - Device Selection Persists (Priority: P2)

**Goal**: Remember selected device and restore on startup if available

**Independent Test**: Select device → Restart app → Verify same device auto-selected (if connected)

### Implementation for User Story 2

- [X] T012 [P] [US2] Update DeviceSelector.__init__ to accept config_store parameter in src/mobile_crawler/ui/widgets/device_selector.py
- [X] T013 [US2] Add _load_selection() method to restore last_device_id on init in src/mobile_crawler/ui/widgets/device_selector.py
- [X] T014 [US2] Modify _on_device_changed() to save last_device_id to config_store in src/mobile_crawler/ui/widgets/device_selector.py
- [X] T015 [US2] Handle graceful fallback when saved device not found in src/mobile_crawler/ui/widgets/device_selector.py
- [X] T016 [US2] Update MainWindow._create_left_panel() to pass user_config_store to DeviceSelector in src/mobile_crawler/ui/main_window.py
- [X] T017 [P] [US2] Update test fixtures in tests/ui/test_device_selector.py to provide mock config_store
- [X] T018 [US2] Add test for device persistence across sessions in tests/ui/test_device_selector.py
- [X] T019 [US2] Add test for graceful fallback when device unavailable in tests/ui/test_device_selector.py

**Checkpoint**: User Story 2 complete - Device selection persists independently

---

## Phase 5: User Story 3 - App Package Selection Persists (Priority: P2)

**Goal**: Remember entered/selected app package and restore on startup

**Independent Test**: Enter package → Restart app → Verify package name restored

### Implementation for User Story 3

- [X] T020 [P] [US3] Update AppSelector.__init__ to accept config_store parameter in src/mobile_crawler/ui/widgets/app_selector.py
- [X] T021 [US3] Add _load_selection() method to restore last_app_package on init in src/mobile_crawler/ui/widgets/app_selector.py
- [X] T022 [US3] Modify _on_text_changed() to save last_app_package to config_store in src/mobile_crawler/ui/widgets/app_selector.py
- [X] T023 [US3] Modify _on_combo_changed() to save last_app_package to config_store in src/mobile_crawler/ui/widgets/app_selector.py
- [X] T024 [US3] Update MainWindow._create_left_panel() to pass user_config_store to AppSelector in src/mobile_crawler/ui/main_window.py
- [X] T025 [P] [US3] Update test fixtures in tests/ui/test_app_selector.py to provide mock config_store
- [X] T026 [US3] Add test for app package persistence across sessions in tests/ui/test_app_selector.py
- [X] T027 [US3] Add test for empty package field handling in tests/ui/test_app_selector.py

**Checkpoint**: User Story 3 complete - App package persists independently

---

## Phase 6: User Story 4 - AI Provider/Model Selection Persists (Priority: P2)

**Goal**: Remember selected AI provider and model, restore on startup

**Independent Test**: Select provider + model → Restart app → Verify both restored

### Implementation for User Story 4

- [X] T028 [P] [US4] Update AIModelSelector.__init__ to accept config_store parameter in src/mobile_crawler/ui/widgets/ai_model_selector.py
- [X] T029 [US4] Add _load_selection() method to restore last_ai_provider and last_ai_model on init in src/mobile_crawler/ui/widgets/ai_model_selector.py
- [X] T030 [US4] Modify _on_provider_changed() to save last_ai_provider to config_store in src/mobile_crawler/ui/widgets/ai_model_selector.py
- [X] T031 [US4] Modify _on_model_changed() to save last_ai_model to config_store in src/mobile_crawler/ui/widgets/ai_model_selector.py
- [X] T032 [US4] Handle graceful fallback when saved model unavailable in src/mobile_crawler/ui/widgets/ai_model_selector.py
- [X] T033 [US4] Update MainWindow._create_left_panel() to pass user_config_store to AIModelSelector in src/mobile_crawler/ui/main_window.py
- [X] T034 [P] [US4] Update test fixtures in tests/ui/test_ai_model_selector.py to provide mock config_store
- [X] T035 [US4] Add test for provider/model persistence across sessions in tests/ui/test_ai_model_selector.py
- [X] T036 [US4] Add test for graceful fallback when model unavailable in tests/ui/test_ai_model_selector.py

**Checkpoint**: User Story 4 complete - AI selection persists independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [X] T037 Run full test suite `pytest tests/` to verify no regressions
- [X] T038 Manual validation per quickstart.md verification steps in specs/001-fix-settings-persistence/quickstart.md
- [X] T039 [P] Update widget docstrings to document config_store parameter

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS User Stories 2-4
- **Phase 3 (US1)**: Verification only - existing code, can parallel with Phase 2
- **Phase 4-6 (US2-4)**: Depend on Phase 2 completion, can run in parallel with each other
- **Phase 7 (Polish)**: Depends on all user stories complete

### User Story Independence

| Story | Can Start After | Dependencies on Other Stories |
|-------|-----------------|-------------------------------|
| US1 (Settings Panel) | Phase 1 | None - already implemented |
| US2 (Device) | Phase 2 | None |
| US3 (App Package) | Phase 2 | None |
| US4 (AI Model) | Phase 2 | None |

### MainWindow Update Consolidation

Tasks T016, T024, T033 all modify `MainWindow._create_left_panel()`. These should be done together or sequentially to avoid merge conflicts:

```python
# All three widgets get config_store in same method:
self.device_selector = DeviceSelector(self._services['device_detection'], self._services['user_config_store'])
self.app_selector = AppSelector(self._services['appium_driver'], self._services['user_config_store'])
self.ai_selector = AIModelSelector(self._services['provider_registry'], self._services['vision_detector'], self._services['user_config_store'])
```

### Parallel Opportunities

```bash
# After Phase 2, these widget implementations can run in parallel:
Phase 4 (US2): T012-T019 (device_selector.py, test_device_selector.py)
Phase 5 (US3): T020-T027 (app_selector.py, test_app_selector.py)  
Phase 6 (US4): T028-T036 (ai_model_selector.py, test_ai_model_selector.py)

# Within each phase, [P] tasks can run in parallel:
T012 [P] and T017 [P] - different files
T020 [P] and T025 [P] - different files
T028 [P] and T034 [P] - different files
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1-2: Verify existing infrastructure
2. Complete Phase 3: Verify SettingsPanel works (already implemented)
3. **STOP and VALIDATE**: Test Settings Panel persistence manually
4. This is already the MVP - settings panel should work!

### Incremental Delivery

1. Phase 3 (US1) → Verify Settings Panel works → MVP Ready
2. Add Phase 4 (US2) → Device persists → Enhanced UX
3. Add Phase 5 (US3) → App package persists → Better UX
4. Add Phase 6 (US4) → AI selection persists → Full feature complete

---

## Notes

- [P] tasks = different files, can run in parallel
- [Story] label maps to spec.md user stories
- US1 is largely verification - SettingsPanel already has persistence code
- US2-4 follow identical pattern: add config_store param → _load_selection() → save on change
- MainWindow changes (T016, T024, T033) touch same method - coordinate or combine
- Total: 39 tasks, ~15 parallelizable, estimated 2-4 hours implementation
