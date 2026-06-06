# Crawler Agent Decision Loop

This document explains how Mobile Crawler decides what to do during an app crawl, where time is spent, and which settings are the safest places to tune speed without damaging crawl quality too much.

The active internal workflow class is now `CrawlerAgent`, located at `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py`. Mobile Crawler now uses the in-repo `crawler_agent` runtime and has transitioned to `crawler` prefixed configuration names.

## Runtime Ownership

Mobile Crawler and `crawler_agent` have different jobs.

Mobile Crawler owns run orchestration:
- CLI and GUI startup.
- Run records in SQLite.
- Session folders and artifact paths.
- Device/package preflight.
- Crawler lifecycle events.
- Step phase tracking.
- Log forwarding.
- Duration limits and cancellation.
- Optional MobSF, PCAPdroid, video, and reporting hooks.

The internal `crawler_agent` runtime owns exploration:
- UI state capture.
- Screenshot capture when configured.
- Accessibility and OmniParser parsing.
- LLM planning.
- LLM action selection.
- Tool registry and ADB-backed actions.
- Shared per-run agent state.

The handoff point is `CrawlerAgentService.execute_exploration_task()`. That service builds a `CrawlerConfig` object from Mobile Crawler settings, creates a `CrawlerAgent`, then runs the agent workflow.

## High-Level Flow

```text
CLI or GUI
  -> CrawlerLoop
    -> CrawlerAgentService
      -> CrawlerAgent
        -> state provider captures UI
        -> LLM chooses next step
        -> tool registry executes action through ADB
        -> result is recorded
        -> repeat until success, max steps, timeout, cancel, or failure
```

The important point: Mobile Crawler does not ask the LLM directly what to click. It delegates to `CrawlerAgent`. Mobile Crawler observes the events and records the run.

## Agent Modes

`CrawlerAgent` has two execution modes.

### Fast Mode: `reasoning=False`

Fast mode uses `FastAgent`.

The FastAgent receives the overall goal, current device state, available tools, and remembered information. It directly decides and executes actions. It does not split the work into a separate planning agent and execution agent.

Typical shape:

```text
Goal + current UI state + tools
  -> FastAgent LLM call
    -> one or more actions through tool registry
      -> completion/failure result
```

Fast mode is usually quicker because it avoids one Manager LLM call per step. The tradeoff is that it may be less careful on complex, multi-screen tasks because planning and action choice are compressed into one agent.

Use this when:
- The app flow is simple.
- The task is short.
- You value speed over detailed reasoning.
- You have strong app cards or predictable UI.

Avoid this when:
- The task needs multi-step planning.
- The app has many similar screens.
- Recovery from failed actions matters.
- The crawl goal is broad or exploratory.

### Reasoning Mode: `reasoning=True`

Reasoning mode uses a Manager/Executor loop.

The Manager decides the plan and next subgoal. The Executor chooses exactly one action for that subgoal and executes it. After the action finishes, the result goes back into shared state, and the Manager plans again.

Typical shape:

```text
Manager phase
  -> capture current UI state
  -> read last action, errors, memory, app card, variables, secrets
  -> LLM produces plan + current subgoal

Executor phase
  -> read current subgoal + current UI state + available tools
  -> LLM produces one action
  -> tool registry executes the action
  -> action result is saved

Loop
  -> Manager reads the new state and decides again
```

This mode is slower but usually better for complex tasks because the Manager can preserve a plan, notice repeated failures, and adjust course.

## What Happens Before the First Decision

Before the first LLM decision, the service and runtime do setup work:

1. `CrawlerAgentService` resolves provider/model/API-key settings.
2. It builds `CrawlerConfig`.
3. It wakes/unlocks the device if configured.
4. It launches or verifies the target package.
5. It initializes `CrawlerAgent`.
6. `CrawlerAgent` connects the Android driver.
7. It creates the UI state provider.
8. It builds the tool registry.
9. It disables unsupported or configured-disabled tools.
10. It creates `ActionContext`.
11. It wires Manager and Executor if reasoning mode is enabled.
12. It captures the device date.

Only after that does the decision loop start.

## Shared State

The Manager, Executor, FastAgent, and tools share a `CrawlerAgentState` object.

Important fields include:
- `instruction`: original crawl goal.
- `step_number`: current loop count.
- `formatted_device_state`: current UI text/tree summary.
- `previous_formatted_device_state`: previous UI summary.
- `screenshot`: current screenshot if captured.
- `phone_state`: package/activity metadata.
- `plan`: Manager's current plan.
- `current_subgoal`: Manager's next subgoal for Executor.
- `progress_summary`: Manager's running summary.
- `action_history`: prior actions.
- `summary_history`: human-readable action summaries.
- `action_outcomes`: success/failure booleans.
- `error_descriptions`: action failure summaries.
- `manager_memory`: Manager planning notes.
- `fast_memory`: FastAgent remembered items.

This is runtime memory for a single crawl. It is separate from `.codex/project-memory/CHANGELOG.md`, which is durable project memory for future Codex sessions.

## Reasoning Mode: Step By Step

### 1. Manager Starts A Step

`CrawlerAgent.run_manager()` checks `max_steps`. If the run has already reached the configured step limit, it finalizes with failure.

Otherwise it increments `shared_state.step_number`.

### 2. Manager Gathers Context

`ManagerAgent.prepare_context()` builds the context used for planning.

It may capture a screenshot if:
- Manager vision is enabled.
- screenshot streaming is enabled.
- trajectory saving is enabled.

Then it calls the state provider:

```text
state_provider.get_state()
```

That returns the current UI state. On Android, this is usually accessibility-first. In `boost` mode, accessibility is tried first and OmniParser is used as fallback when accessibility data is not good enough.

The state provider updates:
- formatted UI text for prompts.
- current focused text.
- raw accessibility elements.
- package/activity metadata.
- previous/current state comparison fields.

### 3. Manager Loads App Context

If app cards are enabled, the Manager loads an app card for the current package. App cards are app-specific hints that can reduce mistakes and save time because the model does not need to rediscover known UI behavior.

App card modes:
- `local`: read local app-card files.
- `server`: fetch from a server.
- `composite`: combine server/local fallback.

Server app cards can add latency. Local app cards are usually faster.

### 4. Manager Builds Prompt Messages

The Manager prompt includes:
- original instruction.
- device date.
- current app card.
- error history when recent actions failed.
- available custom tools.
- available secret IDs.
- custom variables.
- output schema if present.
- platform.
- previous and current UI state.
- Manager memory.
- optional screenshot.
- last thought/action/summary.
- external user messages, if injected mid-run.

The Manager then calls its configured LLM.

### 5. Manager Validates The Response

The Manager response is parsed into:
- `plan`.
- `current_subgoal`.
- `thought`.
- `answer`.
- `success`.
- `memory`.
- `progress_summary`.

If the response is malformed, the Manager may retry up to three times with corrective instructions. These retries improve reliability but can add noticeable time because each retry is another LLM call.

The Manager can finish the task by returning a final answer/request-accomplished result. If it does not finish, it sends `current_subgoal` to the Executor.

### 6. Executor Builds Action Prompt

The Executor receives only the current subgoal from the Manager.

It builds a prompt with:
- original instruction.
- current device state.
- current plan.
- current subgoal.
- progress summary.
- available atomic action signatures.
- last five action history entries.
- available secret IDs.
- custom variables.
- optional screenshot.
- platform.

The Executor intentionally hides flow-control tools like `remember` and `complete` from its prompt.

### 7. Executor Chooses One Action

The Executor calls its configured LLM and expects a structured response containing:
- thought.
- action JSON.
- description.

If parsing fails, it returns an invalid action event rather than silently guessing.

### 8. Tool Registry Executes The Action

The Executor sends the action type and arguments to:

```text
ToolRegistry.execute(action_type, action_args, ActionContext)
```

Typical tool actions include:
- click/tap by indexed element.
- click by coordinates.
- type text.
- type secret.
- scroll/swipe.
- press system buttons.
- open app.
- wait.

The tool uses the Android driver/state provider/ADB through `ActionContext`.

### 9. Result Is Stored

After execution, `CrawlerAgent` updates shared state:
- append action to `action_history`.
- append summary to `summary_history`.
- append success/failure to `action_outcomes`.
- append error summary to `error_descriptions`.
- update `last_action`.
- update `last_summary`.

If the last two actions failed, the runtime sets an error flag so the Manager receives error history in the next planning prompt.

### 10. Loop Continues

The next event is `ManagerInputEvent`, so the Manager sees the new UI state and decides again.

The loop ends when:
- Manager returns a final answer.
- FastAgent completes.
- max steps are reached.
- duration timeout is reached by Mobile Crawler.
- user cancellation is requested.
- device disconnects.
- an unrecoverable error occurs.

## Where Time Is Spent

These are practical estimates, not guarantees. Actual timings depend on provider latency, model, device speed, ADB reliability, app responsiveness, network, OmniParser backend, and whether screenshots/tracing/artifacts are enabled.

| Work Item | Typical Time | Why It Varies |
|-----------|--------------|---------------|
| Device/app preflight | 1-8 seconds | Device locked, app launch delay, ADB response time |
| Accessibility UI state capture | 0.2-2 seconds | UI tree size, ADB/uiautomator state, device load |
| Local OmniParser state capture | 1-6 seconds | Local model speed, screenshot size, hardware |
| Replicate OmniParser state capture | 3-15+ seconds | Network and remote inference latency |
| Manager LLM call | 1-10 seconds | Provider/model/context length/streaming/retries |
| Executor LLM call | 0.5-6 seconds | Provider/model/context length |
| ADB action execution | 0.2-2 seconds | Tap/type/scroll/app wait behavior |
| Adaptive wait after action | 0.1-5 seconds | Action type, wait timeout, UI stability |
| Manager validation retry | +1-10 seconds each | Another LLM call |
| Trajectory/screenshot/tracing write | 0.1-3 seconds | Disk, screenshots, tracing backend |

In reasoning mode, a normal step usually costs:

```text
UI state capture
+ Manager LLM call
+ Executor LLM call
+ action execution
+ UI wait/verification
```

That often means one reasoning step can take roughly 3-20 seconds. If OmniParser remote inference or slow LLMs are involved, a step can be much longer.

In fast mode, a normal step usually costs:

```text
UI state capture
+ FastAgent LLM call
+ action execution
+ UI wait/verification
```

That can be meaningfully faster because it removes the separate Manager call, but it can also waste time if it makes worse decisions and needs more recovery steps.

## Speed Vs Quality Levers

### Safest Speed Improvements

These usually reduce time with limited quality loss.

1. Use faster LLM models for Executor.

The Executor chooses one concrete action. It often does not need the same reasoning depth as the Manager. A fast, cheaper model can work well here if action formatting remains reliable.

2. Keep Manager reasoning on, but use a faster Manager model.

If the current model is slow, switching to a faster model often saves more time than changing prompt logic.

3. Keep parser mode as `boost`.

`boost` uses accessibility first and falls back to OmniParser when needed. This is usually the best speed/quality compromise.

4. Prefer local app cards over server app cards.

App cards improve decisions, but fetching them from a server can add latency. Local cards are usually a good middle ground.

5. Disable trajectory saving unless debugging.

Trajectory/screenshot artifacts are useful for debugging, but they add file I/O and can force screenshot capture.

6. Keep Manager and Executor vision off unless needed.

If accessibility gives enough state, text/tree prompts are faster and cheaper than vision prompts.

7. Tune max steps to the task.

A broad `max_crawl_steps` gives the agent room, but short known flows should not need many steps.

### Medium-Risk Speed Improvements

These can help, but test them carefully.

1. Use `reasoning=False` for simple flows.

FastAgent can be much faster, but complex tasks may become less reliable.

2. Lower adaptive wait timeouts.

Reducing waits can save time on responsive apps. It can also cause premature next-step decisions while the UI is still changing.

3. Reduce Manager context.

Less history and fewer prompt sections can reduce LLM time. The risk is worse recovery and less continuity.

4. Disable app cards.

This removes app-card lookup time, but usually hurts decision quality on app-specific tasks.

5. Use `accessibility` parser mode only.

This avoids OmniParser latency. It can fail when accessibility data is sparse, misleading, or missing important visual controls.

### High-Risk Speed Improvements

These can make runs faster but may significantly reduce reliability.

1. Always use FastAgent.

Good for demos/simple paths, risky for broad exploratory crawls.

2. Disable verification/context guards.

This can hide app switches, stale UI, or failed actions.

3. Use very small models for Manager.

The Manager is responsible for planning and recovery. Weak planning can increase total runtime by creating more failed steps.

4. Aggressively lower wait timeouts below app animation/network timing.

The agent may act on stale state and produce cascading failures.

5. Use OmniParser only with a slow remote backend.

This can improve visual grounding, but every state capture may become expensive.

## Recommended Profiles

### Balanced Default

Best for most app crawls.

```text
reasoning=True
ui_parser_mode=boost
manager.vision=False
executor.vision=False
trajectory saving=off
local app cards=on
max steps=task dependent, often 10-20
```

Why: keeps planning quality while avoiding expensive vision/remote parsing unless fallback is needed.

### Fast Known-Flow Profile

Best for short flows like opening a screen, tapping through a known form, or checking one feature.

```text
reasoning=False
ui_parser_mode=accessibility or boost
fast_agent.vision=False
local app cards=on
max steps=5-10
```

Why: removes Manager/Executor split and minimizes per-step LLM calls.

Risk: weaker recovery if the UI differs from expectation.

### Visual-Fallback Profile

Best when accessibility misses important controls.

```text
reasoning=True
ui_parser_mode=boost
manager.vision=False
executor.vision=False initially
local OmniParser preferred over Replicate
```

Why: starts with accessibility and uses OmniParser only when needed.

Escalate to vision prompts only if the text/tree state is not enough.

### Debug Profile

Best when investigating why the agent made a bad decision.

```text
reasoning=True
ui_parser_mode=boost or omniparser
trajectory saving=on
tracing=on if configured
debug logging=on
screenshots=on if needed
```

Why: maximizes observability.

Risk: slower runs and more artifacts.

## What To Add For Better Speed Without Losing Much Quality

### 1. Per-Phase Model Selection In The UI

The runtime already supports separate LLM profiles:
- manager.
- executor.
- fast_agent.
- app_opener.
- structured_output.

The UI/config could expose this cleanly so the Manager can use a smarter model while the Executor uses a faster model.

Expected impact: high speed benefit, moderate implementation effort, low quality risk if tested.

### 2. Step Timing Metrics

Add timing around:
- state capture.
- app-card load.
- Manager LLM.
- Manager validation retry count.
- Executor LLM.
- tool execution.
- adaptive wait.
- verification.

Expected impact: no direct speedup, but very high diagnostic value. It tells you what to optimize instead of guessing.

### 3. Token/Context Budget Controls

Add config for:
- max action history entries.
- whether previous UI state is included.
- whether Manager memory is included every step.
- whether custom tool descriptions are repeated every step.

Expected impact: medium speed benefit, medium quality risk.

### 4. Local OmniParser Health And Warmup

If using local OmniParser, add a warmup/health check before the crawl starts. That avoids the first fallback step paying a surprise startup cost.

Expected impact: medium speed benefit for visual flows, low quality risk.

### 5. App-Specific Cached Hints

App cards already help. Improve them with concise app-specific navigation maps and common element labels. Keep them short; huge app cards slow down prompts.

Expected impact: medium to high quality benefit, possible speed benefit through fewer mistakes.

### 6. Executor Action Cache For Repeated Screens

For repeated screens, cache a successful action pattern keyed by package/activity plus normalized UI signature.

Expected impact: potentially high speed benefit, higher implementation complexity.

Risk: stale cache can click the wrong thing after UI changes.

### 7. Early Completion Checks

Add lightweight checks before calling the Manager when the last action clearly reached the goal condition.

Expected impact: medium speed benefit for known tasks.

Risk: false positives if completion detection is weak.

## What To Remove Or Keep Disabled For Speed

Usually keep disabled unless debugging or explicitly needed:
- trajectory saving.
- Langfuse screenshot upload.
- full vision prompts.
- remote OmniParser as first-choice parser.
- PCAPdroid capture.
- video recording.
- MobSF post-run analysis during interactive debugging.

These features are useful, but they add time outside the core decision loop.

## What Not To Remove Casually

Do not casually remove:
- target-app preflight.
- wake/unlock preflight.
- app-switch guards.
- action verification.
- adaptive waits.
- error escalation back to Manager.

These protect reliability. Removing them can make individual steps faster but create more failed runs.

## Practical Timing Formula

For reasoning mode:

```text
total_run_time =
  startup_preflight
  + sum(each step:
      state_capture
      + manager_llm
      + optional_manager_retries
      + executor_llm
      + action_execution
      + adaptive_wait
      + verification/logging
    )
  + cleanup/report hooks
```

For fast mode:

```text
total_run_time =
  startup_preflight
  + sum(each step:
      state_capture
      + fast_agent_llm
      + action_execution
      + adaptive_wait
      + verification/logging
    )
  + cleanup/report hooks
```

This is why a faster model or fewer steps usually beats tiny micro-optimizations. One avoided LLM call or one avoided bad step can save more time than shaving milliseconds from local code.

## Suggested Next Improvements

Best next changes if the goal is faster runs without major quality loss:

1. Add timing metrics per Manager/Executor/action phase.
2. Expose separate Manager and Executor model settings in the UI.
3. Add a "fast known-flow" preset that sets `reasoning=False`, lower max steps, and accessibility/boost parser mode.
4. Add a "balanced crawl" preset that keeps `reasoning=True`, `boost`, local app cards, and no trajectory.
5. Add a "debug crawl" preset that enables trajectory/tracing/logging but warns that it is slower.

The timing metrics should come first. Without them, the project cannot tell whether the slow part is LLM latency, OmniParser, ADB state capture, waits, or artifact work.
