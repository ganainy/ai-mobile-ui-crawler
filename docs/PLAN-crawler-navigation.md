# AI Harness Crawler Navigation Improvements

Plan to improve the Android/iOS application navigation in the AI mobile crawler. The goal is to move from a flat, purely exploratory "discover as much as possible" prompt to a robust, structured navigation harness.

---

## Overview

Currently, the mobile crawler utilizes a flat system prompt directing the AI to explore the application broadly and discover as much as possible. This approach is prone to:
1. **Inefficient Navigation loops**: Lacking a structured state machine, the crawler gets stuck on repetitive UI sequences.
2. **Form Validation Blockers**: When encountering forms (login, sign-up, setup), the agent either guesses values or injects basic static credentials, frequently failing validation.
3. **Lack of Guided Progress**: There is no distinction between critical initialization steps (e.g., logging in or completing onboarding) and subsequent general exploration.

This plan details three core improvements (as selected by the user):
1. **Hybrid Explorer Strategy**: Guided scenario goals are completed first (e.g., login, onboarding), followed by systematic exploration to maximize unique screens.
2. **Layout XML Hashing & FSM**: Reliable unique screen identification using sanitized DOM hashes to build a dynamic runtime State Transition Graph for loop detection and backtracking.
3. **Context-Aware Input Dictionary**: Dynamic matching of input field labels/attributes to synthetic values (names, addresses, standard credentials) to bypass form validation blocks.

---

## User Review Required

> [!IMPORTANT]
> **API & Configuration Changes**
> - The config manager schema will be updated to support a new `credentials_dictionary` and `guided_scenarios` keys in `config.yaml`.
> - The database schema will be updated to persist the state transition graph (unique states and transitions) so runs can be fully audited.
> - The prompt template files under `src/mobile_crawler/domain/crawler_agent/config/prompts/` will be updated, which may affect custom prompts if overrides are used.

---

## Open Questions

None. The user has explicitly selected:
- **C. Hybrid Explorer (Recommended)**
- **Option B (Layout XML Hashing)**
- **Option A (Context-Aware Input Dictionary)**

---

## Proposed Changes

### 1. State Representation & State Graph (FSM)
This component adds layout hashing capability and a dynamic FSM state tracker to identify loops, map unexplored navigation paths, and track unique screens accurately.

#### [NEW] [state_graph.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/state_graph.py)
- Implement `StateGraphTracker` class.
- Add `compute_layout_hash(a11y_tree: list) -> str` to filter out dynamic content (e.g., clocks, loaders, ads, battery icons) and hash the remaining structural components.
- Add methods to track visited states, transitions (from state A to state B via action X), and calculate backtracking paths when stuck.

#### [MODIFY] [provider.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/crawler_agent/tools/ui/provider.py)
- Integrate layout hashing directly into state capture so `UIState` returned by `AndroidStateProvider.get_state()` contains the filtered layout hash.

---

### 2. Form & Input Grounding
This component manages intelligent input data generation when forms are encountered.

#### [NEW] [input_dictionary.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/input_dictionary.py)
- Implement `ContextAwareInputDictionary` matching input identifiers (resource IDs, hints, labels, text) using regex and fuzzy matching to realistic values (e.g., valid email, name, phone, address).
- Provide fallback values and interface to load custom credential dictionaries from config.

#### [MODIFY] [prompt_builder.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/prompt_builder.py)
- Modify `PromptBuilder.build_user_prompt()` to include matched synthetic values for all detected input fields in `available_actions` or `ocr_grounding` metadata.
- Supply the LLM with the exact synthetic values it should type, reducing hallucinated form entries.

---

### 3. Exploration Strategy & AI Harness
This component coordinates guided scenarios and systematic exploration.

#### [MODIFY] [prompts.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/prompts.py)
- Refactor `DEFAULT_SYSTEM_PROMPT` to support the Hybrid Explorer flow.
- Instruct the agent to strictly follow the current guided subgoal before beginning broad exploration.

#### [MODIFY] [crawler_agent_service.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/crawler_agent_service.py)
- Modify `_create_exploration_goal` to parse the configured `guided_scenarios` and inject them as an ordered checklist in the goal description.
- Initialize `StateGraphTracker` and `ContextAwareInputDictionary` at start of step tracking.

#### [MODIFY] [manager_agent.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/crawler_agent/agent/manager/manager_agent.py)
- Inject state graph context (current loops, depth, and back-track suggestions) into the Manager LLM system prompt variables.
- Update `system.jinja2` prompt template to guide the manager on how to resolve loops and complete guided scenarios.

---

## Task Breakdown

### Task 1: Foundation (State Hashing and Graphs)
- **Agent**: `mobile-developer`
- **Skill**: `mobile-design`
- **Priority**: P0
- **Dependencies**: None
- **INPUT**: Active accessibility tree list
- **OUTPUT**: Filtered stable layout XML hash and state graph transition node
- **VERIFY**: Unit test verifying layout hash ignores clock updates/spinners but changes on page layout shifts.

### Task 2: Form Input Dictionary
- **Agent**: `mobile-developer`
- **Skill**: `clean-code`
- **Priority**: P0
- **Dependencies**: None
- **INPUT**: UI text element attributes
- **OUTPUT**: Matched synthetic data string (email, address, name)
- **VERIFY**: Unit test verifying input dictionary matches "email_address" to a valid email string.

### Task 3: Prompt and Context Upgrades
- **Agent**: `mobile-developer`
- **Skill**: `mobile-design`
- **Priority**: P1
- **Dependencies**: Task 1, Task 2
- **INPUT**: Layout hash and matched input fields
- **OUTPUT**: Upgraded prompt structure with loop warnings and recommended inputs
- **VERIFY**: Prompt template render output inspection.

### Task 4: Hybrid Explorer Integration
- **Agent**: `mobile-developer`
- **Skill**: `mobile-design`
- **Priority**: P1
- **Dependencies**: Task 3
- **INPUT**: Guided scenarios configuration list
- **OUTPUT**: Sequence of guided subgoals followed by random-exploration mode
- **VERIFY**: Run crawler on a test package (e.g. settings app) with a login scenario, verify it resolves the scenario before general navigation.

---

## Verification Plan

### Automated Tests
Run the test suite to ensure existing crawler flows are unaffected:
```powershell
pytest tests/infrastructure/test_ai_interaction_service.py
pytest tests/domain/test_crawler_agent.py
```

### Manual Verification
1. Start the crawler UI or CLI on the default target package:
   ```powershell
   python run_cli.py --config config.yaml
   ```
2. Inspect the crawler's logs and `crawler_trace.jsonl` to verify:
   - Layout hashes are calculated correctly on each step.
   - Loop detection fires when visiting revisited screens.
   - Synthetic inputs are populated and correctly keyed into fields.
3. Validate that guided goals are completed first before general exploration begins.

---

## ✅ PHASE X: Final Verification
- [ ] Code compiles and builds cleanly
- [ ] All unit and integration tests pass
- [ ] No purple/violet hex codes in changes
- [ ] Socratic Gate was respected
