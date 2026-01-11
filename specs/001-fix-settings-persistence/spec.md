# Feature Specification: Fix Settings Persistence

**Feature Branch**: `001-fix-settings-persistence`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: User description: "the settings are not persisting when app is restarted, we need to change that"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Settings Panel Values Persist Across Sessions (Priority: P1)

As a user, when I configure API keys, system prompt, crawl limits, and test credentials in the Settings panel and click "Save Settings", those values should be restored when I restart the application.

**Why this priority**: This is the core persistence functionality. API keys are essential for the crawler to function, and re-entering them every session is frustrating and time-consuming.

**Independent Test**: Can be fully tested by entering values in Settings panel, saving, restarting the app, and verifying all values are restored. Delivers immediate value by eliminating repetitive data entry.

**Acceptance Scenarios**:

1. **Given** I have entered a Gemini API key and clicked "Save Settings", **When** I restart the application, **Then** the Gemini API key field shows the previously saved key (masked as password).

2. **Given** I have entered an OpenRouter API key and clicked "Save Settings", **When** I restart the application, **Then** the OpenRouter API key field shows the previously saved key (masked as password).

3. **Given** I have configured max steps to 200 and max duration to 600 seconds, **When** I restart the application, **Then** those values appear in the spinboxes.

4. **Given** I have entered a custom system prompt and clicked "Save Settings", **When** I restart the application, **Then** the system prompt text area contains the saved text.

5. **Given** I have entered test credentials (username and password) and clicked "Save Settings", **When** I restart the application, **Then** the credentials are restored.

---

### User Story 2 - Device Selection Persists Across Sessions (Priority: P2)

As a user, when I select an Android device from the dropdown, that selection should be remembered when I restart the application (if the device is still available).

**Why this priority**: Device selection is required for every crawl session. If the same device is typically used, re-selecting it each time adds friction.

**Independent Test**: Can be fully tested by selecting a device, restarting the app, and verifying the same device is auto-selected if available.

**Acceptance Scenarios**:

1. **Given** I have selected device "Xiaomi 2107113SG (279cb9b1)", **When** I restart the application and that device is connected, **Then** the device dropdown shows the previously selected device.

2. **Given** I have selected a device that is no longer connected, **When** I restart the application, **Then** the device dropdown shows "No device selected" or prompts selection, and no error occurs.

3. **Given** I have never selected a device, **When** I start the application, **Then** the device dropdown shows the default "No device selected" state.

---

### User Story 3 - App Package Selection Persists Across Sessions (Priority: P2)

As a user, when I enter or select an app package name, that selection should be remembered when I restart the application.

**Why this priority**: App package is required for every crawl and typically the same app is tested repeatedly during development cycles.

**Independent Test**: Can be fully tested by entering an app package, restarting the app, and verifying the package name is restored.

**Acceptance Scenarios**:

1. **Given** I have entered package "shop.shop_apotheke.com.shopapotheke", **When** I restart the application, **Then** the app package input shows the previously entered package name.

2. **Given** I have selected a package from the installed apps list, **When** I restart the application, **Then** the app package input shows that package name.

3. **Given** I have cleared the app package field, **When** I restart the application, **Then** the app package input is empty.

---

### User Story 4 - AI Provider and Model Selection Persists Across Sessions (Priority: P2)

As a user, when I select an AI provider (Gemini/OpenRouter) and a vision model, those selections should be remembered when I restart the application.

**Why this priority**: AI model selection is essential for the crawler's vision capabilities and typically remains consistent across sessions.

**Independent Test**: Can be fully tested by selecting provider and model, restarting the app, and verifying selections are restored.

**Acceptance Scenarios**:

1. **Given** I have selected "Gemini" as AI provider and "models/gemini-2.0-flash" as vision model, **When** I restart the application, **Then** both selections are restored.

2. **Given** I have selected a model that is no longer available (e.g., deprecated), **When** I restart the application, **Then** a graceful fallback occurs showing the model as "unavailable" or prompting re-selection.

3. **Given** the saved provider requires an API key that is no longer configured, **When** I restart the application, **Then** the provider is restored but the model list may be empty until an API key is provided.

---

### Edge Cases

- What happens when the database file is corrupted or deleted? System should handle gracefully and use defaults.
- What happens when encrypted secrets cannot be decrypted (machine change)? System should clear invalid secrets and prompt re-entry.
- What happens when settings were saved in an older app version with different schema? Migration should handle schema changes.
- What happens when the app data directory is not writable? System should notify user and continue with in-memory defaults.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist all Settings panel values (API keys, system prompt, crawl limits, test credentials) to the user configuration database when "Save Settings" is clicked.

- **FR-002**: System MUST restore all Settings panel values from the database when the application starts.

- **FR-003**: System MUST persist the selected device identifier when a device is selected from the dropdown.

- **FR-004**: System MUST restore the previously selected device on startup if that device is currently connected.

- **FR-005**: System MUST persist the selected app package name when entered or selected.

- **FR-006**: System MUST restore the previously selected app package name on startup.

- **FR-007**: System MUST persist the selected AI provider and model when a selection is made.

- **FR-008**: System MUST restore the previously selected AI provider and model on startup.

- **FR-009**: System MUST encrypt sensitive data (API keys, passwords) before storing in the database.

- **FR-010**: System MUST handle missing or unavailable previously-selected devices/models gracefully without errors.

- **FR-011**: System MUST use sensible defaults when no previously saved values exist.

### Key Entities

- **User Settings**: Configuration values including API keys (encrypted), system prompts, crawl limits, and test credentials.
- **Device Selection**: Reference to the currently selected Android device by device identifier.
- **App Selection**: The selected Android app package name.
- **AI Configuration**: Selected AI provider name and model identifier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure all settings once and have them automatically restored in subsequent sessions without manual re-entry.

- **SC-002**: Time to start a crawl session is reduced by eliminating the need to re-configure device, app, and AI settings each time.

- **SC-003**: 100% of configuration fields that have been explicitly saved are restored correctly after app restart.

- **SC-004**: When previously selected devices/models are unavailable, the user receives clear feedback and can make a new selection without application errors.

- **SC-005**: Sensitive data (API keys, passwords) remains encrypted at rest and is not exposed in plain text in storage.

## Assumptions

- The SQLite database storage mechanism already exists and functions correctly for the Settings panel.
- The existing encryption mechanism for secrets (machine-bound Fernet encryption) is sufficient.
- Device detection, app listing, and model fetching APIs remain available and consistent.
- Users typically use the same device, app, and AI model configuration across multiple sessions.
