---
author: claude
date: 2026-09-19
---
# Issue #7: App Accounts implemented

- New `infrastructure/app_account_store.py`: `AppAccount` + `AppAccountStore`, one account per package. Username/address override in settings key `app_account::<pkg>`, password encrypted in secrets (`app_account_password::<pkg>`). No global fallback.
- `PromptBuilder.build_system_prompt(app_package)` shows only that package's account, or says "No App Account exists for <pkg>". `ContextAwareInputDictionary(app_account=...)` uses it; without one username/password fields get the generic value.
- Settings: global username/password removed, group renamed "Form Fill Data"; new "App Account" group under Guided Scenarios (edit fields + Delete Account), loaded on app select, saved on Save.
- Live path: `PromptBuilder` is unused in production, so `CrawlerAgentService._create_exploration_goal` appends a "LOGIN AND FORM DATA" section via `prompt_builder.format_login_and_form_data`. Without an account the agent is told none exists and not to invent one; `InputDictionary` suggests empty username/password.
- Legacy global `test_username`/`test_password` are purged on Settings load. Settings Reset no longer touches the per-app fields.
- Follow-ups: `address_override` is stored but unread until #8; the UI is a single-account form, not a list.
- Test env quirk: `UserConfigStore` secrets shell out to `powershell`, which fails under pytest stdin capture; run with `pytest -s`.
