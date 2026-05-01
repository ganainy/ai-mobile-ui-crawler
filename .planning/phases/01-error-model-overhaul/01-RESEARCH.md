# Phase 1: Error Model Overhaul - Research

**Researched:** 2026-05-01
**Domain:** Python exception taxonomy, structured error logging, fail-closed design for crawl loops
**Confidence:** HIGH

## Summary

The mobile-crawler codebase has a pervasive error suppression problem: 28 bare `except Exception:` blocks and 1 bare `except:` block exist across the `src/` tree, with at least 3 in crawl-critical paths (crawler loop event emission, DroidRun log handler, database migration). The crawl loop's `_emit_event` method silently swallows all listener exceptions with `except Exception: continue`, which means recorder and checkpoint failures produce no signal. The codebase currently has zero typed exception classes -- all errors flow as generic `Exception` instances with no classification.

This phase must introduce a typed exception hierarchy that classifies errors as retryable, fatal, or operator-actionable; wire structured context (run_id, step_id, action type, device state) into every error log entry; and enforce fail-closed semantics on recorder/checkpoint paths so a persistence failure halts the run rather than continuing silently. The existing `LoggingService`/`LogSink` architecture and `CrawlerEventListener` event contract are the extension points.

**Primary recommendation:** Create a `src/mobile_crawler/domain/errors.py` module with a three-tier exception hierarchy rooted at `CrawlerError`. Replace blanket handlers in crawl-critical code first (crawler_loop, droidrun_agent_service, database). Enrich the `CrawlerEventListener.on_error` signature to carry structured error context. Fail-closed on all repository write paths.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Typed exception taxonomy | Domain | -- | Exception classes encode domain semantics (retryable/fatal/actionable) -- a domain concern |
| Structured error logging | Core (log_sinks, logging_service) | Domain | Core owns log routing; domain provides error context objects |
| Fail-closed recorder/checkpoint | Infrastructure (repositories) | Core (crawler_loop) | Infrastructure repositories must raise typed errors on write failures; core loop must halt on them |
| Event listener error propagation | Core (crawler_event_listener) | -- | Listener contract defines what error information flows to UI/CLI |
| Blanket handler replacement | Core + Domain + Infrastructure | -- | Every layer has blanket catches to replace |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.9+ (stdlib) | Exception context data classes | Already used project-wide for DTOs [VERIFIED: codebase grep] |
| Python stdlib `logging` | 3.9+ (stdlib) | Structured error log emission | Already used project-wide via `logging.getLogger(__name__)` [VERIFIED: codebase] |
| Python stdlib `enum` | 3.9+ (stdlib) | Error severity/classification enum | Already used in `CrawlState`, `LogLevel`, `CrawlControlState` [VERIFIED: codebase] |
| pytest | 7.0+ | Test framework | Already configured in pyproject.toml [VERIFIED: pyproject.toml] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 7.0+ | Exception classification tests | `pytest.raises(MyTypedError)` for every error class |
| unittest.mock | stdlib | Mocking repository failures | Testing fail-closed behavior without real DB |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom exception hierarchy | `tenacity` retry library | Tenacity adds retry logic but not error taxonomy. Our phase needs taxonomy first; retries are Phase 2+ [ASSUMED] |
| Custom exception hierarchy | `pydantic` for error context validation | Adds a heavy dependency for simple dataclass context. Overkill for exception payloads [ASSUMED] |

**Installation:**
```bash
# No new packages needed -- this phase uses only Python stdlib
```

**Version verification:** All dependencies are stdlib (no pip packages to verify).

## Architecture Patterns

### System Architecture Diagram

```
                    Crawl Loop (crawler_loop.py)
                           |
                  catches typed exceptions
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
    Typed Exception   Error Context    Fail-Closed
    Hierarchy         Enrichment       Check
    (errors.py)       (ErrorContext)   (recorders)
         |              |              |
         v              v              v
    CrawlerError     run_id,        Repository write
    + subclasses     step_id,       must raise
    (Retryable,      action_type,   typed error
    Fatal,           device_state   not swallow
    OperatorActionable)
```

Data flow:
1. Crawl loop catches a low-level exception (subprocess.TimeoutExpired, sqlite3.OperationalError, etc.)
2. Loop wraps it in a typed exception from the hierarchy with an `ErrorContext` payload
3. Typed exception is logged via structured logging (includes run_id, step_id, action, device state)
4. If fatal or on recorder/checkpoint path, the loop halts (fail-closed)
5. If retryable, the loop may retry (future: Phase 2 retry budget)
6. Error event propagates to listeners via enriched `on_error` call

### Recommended Project Structure

```
src/mobile_crawler/
  domain/
    errors.py                    # NEW: typed exception taxonomy + ErrorContext
    models.py                    # EXISTS: ActionResult, etc. (no changes)
  core/
    crawler_loop.py              # MODIFY: replace blanket handlers, fail-closed
    crawler_event_listener.py    # MODIFY: enrich on_error signature
    logging_service.py           # EXISTS: structured logging (may add error-specific methods)
    log_sinks.py                 # EXISTS: log sinks (may add error context formatting)
  infrastructure/
    database.py                  # MODIFY: replace except: pass in migrate_schema
    run_repository.py            # MODIFY: raise typed errors on write failures
tests/
  domain/
    test_errors.py               # NEW: taxonomy tests
  core/
    test_droidrun_crawler_loop.py # MODIFY: add fail-closed tests
    test_error_handling.py       # NEW: structured error logging tests
```

### Pattern 1: Typed Exception Hierarchy

**What:** A three-tier exception tree rooted at `CrawlerError` with automatic context enrichment.
**When to use:** Every catch point in crawl-critical code wraps or raises these instead of generic `Exception`.

```python
# Source: standard Python exception design pattern
import enum
from dataclasses import dataclass, field
from typing import Optional, Any


class ErrorSeverity(enum.Enum):
    """Classification of crawler error severity."""
    RETRYABLE = "retryable"           # Transient; worth retrying (timeout, network blip)
    FATAL = "fatal"                   # Unrecoverable; must halt run
    OPERATOR_ACTIONABLE = "operator_actionable"  # Needs human intervention


@dataclass
class ErrorContext:
    """Structured context for error logging."""
    run_id: Optional[int] = None
    step_id: Optional[int] = None
    action_type: Optional[str] = None
    device_state: Optional[dict] = None
    extra: dict = field(default_factory=dict)


class CrawlerError(Exception):
    """Base exception for all crawler errors."""

    def __init__(self, message: str, *, context: Optional[ErrorContext] = None,
                 severity: ErrorSeverity = ErrorSeverity.FATAL, cause: Optional[Exception] = None):
        super().__init__(message)
        self.context = context or ErrorContext()
        self.severity = severity
        self.__cause__ = cause

    def to_log_dict(self) -> dict:
        """Convert to structured dict for logging."""
        return {
            "error_type": self.__class__.__name__,
            "severity": self.severity.value,
            "message": str(self),
            "run_id": self.context.run_id,
            "step_id": self.context.step_id,
            "action_type": self.context.action_type,
            "device_state": self.context.device_state,
            "cause": str(self.__cause__) if self.__cause__ else None,
        }


class RetryableError(CrawlerError):
    """Transient error that may succeed on retry."""
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("severity", ErrorSeverity.RETRYABLE)
        super().__init__(message, **kwargs)


class FatalError(CrawlerError):
    """Unrecoverable error that must halt the run."""
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("severity", ErrorSeverity.FATAL)
        super().__init__(message, **kwargs)


class OperatorActionableError(CrawlerError):
    """Error requiring human intervention (e.g., device disconnected, API key invalid)."""
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("severity", ErrorSeverity.OPERATOR_ACTIONABLE)
        super().__init__(message, **kwargs)


class DeviceError(RetryableError):
    """Device communication error (ADB timeout, device disconnected)."""
    pass


class RecorderError(FatalError):
    """Persistence/recorder failure -- must halt run (fail-closed)."""
    pass


class CheckpointError(FatalError):
    """Checkpoint write failure -- must halt run (fail-closed)."""
    pass


class AIServiceError(RetryableError):
    """AI provider request failure (rate limit, timeout, invalid response)."""
    pass
```

### Pattern 2: Fail-Closed Recorder Wrapper

**What:** Repository write methods raise `RecorderError`/`CheckpointError` instead of silently swallowing failures.
**When to use:** All write paths in run_repository, step_log_repository, and database schema migrations.

```python
# Source: fail-closed design pattern
from mobile_crawler.domain.errors import RecorderError, ErrorContext

def update_run_stats(self, run_id: int, **kwargs) -> bool:
    try:
        with closing(self.db_manager.get_connection()) as conn:
            # ... execute SQL ...
            conn.commit()
            return updated
    except sqlite3.OperationalError as e:
        raise RecorderError(
            f"Failed to update run stats for run_id={run_id}: {e}",
            context=ErrorContext(run_id=run_id),
            cause=e,
        ) from e
```

### Pattern 3: Structured Error Logging

**What:** Every caught exception is logged with full context before being re-raised or handled.
**When to use:** Every `except` block in crawl-critical code.

```python
# Source: structured logging pattern
import logging
import json

logger = logging.getLogger(__name__)

try:
    result = await self._droidrun_agent_service.execute_exploration_task(...)
except CrawlerError as e:
    logger.error(json.dumps(e.to_log_dict()))
    raise  # Re-raise for outer handler
except Exception as e:
    # Wrap unknown exceptions
    wrapped = FatalError(f"Unexpected error: {e}", context=ErrorContext(run_id=run_id), cause=e)
    logger.error(json.dumps(wrapped.to_log_dict()))
    raise wrapped from e
```

### Anti-Patterns to Avoid

- **Swallowing exceptions in event listeners:** The current `_emit_event` uses `except Exception: continue`. Instead, classify: if the failing listener IS the recorder/checkpoint, raise `RecorderError` to halt the run. Only UI/notification listeners may have their exceptions caught and logged. [VERIFIED: crawler_loop.py:283-286]
- **Adding `except Exception:` at the hierarchy root:** The `CrawlerError` base class should NOT have blanket catches. Each catch point must be explicit about which typed exceptions it handles. [ASSUMED]
- **Enriching context after the fact:** Error context must be populated at the catch site where the context is available, not reconstructed later. [ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic for transient errors | Custom retry loops | Future: `tenacity` or simple retry decorator in Phase 2 | Retry budget, backoff, jitter are deceptively complex |
| Error context serialization | Custom JSON formatter | `dataclasses.asdict()` + `json.dumps()` | dataclass serialization is built-in and tested |
| Exception chaining | Manual cause tracking | Python's `raise X from Y` syntax | `__cause__` is set automatically, traceback shows full chain |

**Key insight:** This phase only needs the taxonomy and fail-closed enforcement. Retry policies, circuit breakers, and adaptive backoff belong to later phases.

## Runtime State Inventory

> This is a greenfield feature addition (new exception classes, modifying catch blocks). No stored data, service configs, OS registrations, secrets, or build artifacts reference the exception class names. No migration needed.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None -- exception classes are code-only, not persisted by name | None |
| Live service config | None -- no external services reference exception types | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None -- pure Python, no compiled artifacts | None |

## Common Pitfalls

### Pitfall 1: Over-broad exception replacement
**What goes wrong:** Replacing ALL `except Exception:` blocks in the entire codebase, including non-critical UI/notification paths where silent failure is acceptable.
**Why it happens:** Success criterion says "no bare except:pass in crawl loop or device interaction code" -- but developers interpret this as the entire codebase.
**How to avoid:** Scope replacement strictly to: (1) `core/crawler_loop.py`, (2) `domain/droidrun_agent_service.py`, (3) `infrastructure/database.py` migration, (4) repository write methods. UI widget error handlers and logging infrastructure error handlers may keep defensive catches but must log the exception instead of bare `pass`.
**Warning signs:** PR touches 20+ files; test count balloons unnecessarily.

### Pitfall 2: Breaking the event listener contract
**What goes wrong:** Changing `on_error(run_id, step_number, error)` signature breaks all existing listener implementations (SignalAdapter, JSONEventListener, TestListener).
**Why it happens:** Adding structured context requires extending the signature.
**How to avoid:** Either (a) keep `on_error` accepting `Exception` but pass `CrawlerError` instances (duck typing -- all listeners that do `str(error)` still work), or (b) add a new method `on_structured_error` alongside the existing one. Option (a) is strongly preferred for backward compatibility.
**Warning signs:** Existing listener tests break after error model changes.

### Pitfall 3: Fail-closed on non-critical paths
**What goes wrong:** Making UI update failures or log sink failures halt the crawl run.
**Why it happens:** Applying fail-closed too broadly. The requirement says "recorder or checkpoint failure" specifically.
**How to avoid:** Only raise `RecorderError`/`CheckpointError` from repository write methods (run_repository, step_log_repository, ai_interaction_repository). Event listener notification failures should be logged but not halt the run.
**Warning signs:** Crawler halts when a UI widget throws during rendering.

### Pitfall 4: Losing the original traceback
**What goes wrong:** Wrapping exceptions with `raise CrawlerError(msg)` instead of `raise CrawlerError(msg) from e`, losing the original traceback.
**Why it happens:** Forgetting the `from` clause.
**How to avoid:** Always use `raise TypedError(...) from e` when wrapping. Add a Ruff rule or code review checklist item.
**Warning signs:** Error logs show only the wrapper message, not the original cause chain.

### Pitfall 5: Database migration regression
**What goes wrong:** Replacing `except Exception: pass` in `migrate_schema()` (database.py:305) without understanding that SQLite migrations can fail for benign reasons (column already exists after partial migration).
**Why it happens:** The existing `except: pass` was masking `ALTER TABLE` failures on duplicate columns.
**How to avoid:** Before removing the blanket catch, refactor migration to use `PRAGMA table_info` checks first (already partially done -- the code checks before ALTER). Then catch only `sqlite3.OperationalError` and log it. Never silence migration failures entirely.
**Warning signs:** Fresh install fails with "column already exists" after error model changes.

## Code Examples

### Exception taxonomy module (complete)

```python
# src/mobile_crawler/domain/errors.py
# Source: design pattern for typed exception hierarchies

import enum
from dataclasses import dataclass, field
from typing import Optional, Any, Dict


class ErrorSeverity(enum.Enum):
    """Classification of crawler error severity."""
    RETRYABLE = "retryable"
    FATAL = "fatal"
    OPERATOR_ACTIONABLE = "operator_actionable"


@dataclass
class ErrorContext:
    """Structured context attached to every crawler error."""
    run_id: Optional[int] = None
    step_id: Optional[int] = None
    action_type: Optional[str] = None
    device_state: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "action_type": self.action_type,
            "device_state": self.device_state,
            **self.extra,
        }


class CrawlerError(Exception):
    """Base exception for all typed crawler errors."""
    severity: ErrorSeverity = ErrorSeverity.FATAL

    def __init__(
        self,
        message: str,
        *,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.context = context or ErrorContext()
        self.__cause__ = cause

    def to_log_dict(self) -> Dict[str, Any]:
        result = {
            "error_type": type(self).__name__,
            "severity": self.severity.value,
            "message": str(self),
            **self.context.to_dict(),
        }
        if self.__cause__:
            result["cause_type"] = type(self.__cause__).__name__
            result["cause_message"] = str(self.__cause__)
        return result


class RetryableError(CrawlerError):
    """Transient error that may succeed on retry."""
    severity = ErrorSeverity.RETRYABLE


class FatalError(CrawlerError):
    """Unrecoverable error that must halt the run."""
    severity = ErrorSeverity.FATAL


class OperatorActionableError(CrawlerError):
    """Error requiring human intervention."""
    severity = ErrorSeverity.OPERATOR_ACTIONABLE


# Domain-specific exceptions
class DeviceError(RetryableError):
    """Device communication error (ADB timeout, disconnected device)."""


class RecorderError(FatalError):
    """Persistence failure -- must halt the run (fail-closed)."""


class CheckpointError(FatalError):
    """Checkpoint write failure -- must halt the run (fail-closed)."""


class AIServiceError(RetryableError):
    """AI provider request failure (rate limit, timeout, invalid response)."""


class DeviceDisconnectedError(OperatorActionableError):
    """Device physically disconnected -- operator must reconnect."""
```

### Fail-closed event emission in crawler loop

```python
# Source: pattern for replacing blanket handler in crawler_loop.py _emit_event

def _emit_event(self, method_name: str, *args) -> None:
    """Emit events to listeners. Recorder failures halt the run."""
    for listener in list(self.event_listeners):
        handler = getattr(listener, method_name, None)
        if handler:
            try:
                handler(*args)
            except RecorderError:
                # Fail-closed: recorder failure must halt the run
                raise
            except Exception as e:
                # Log but don't halt for non-critical listener failures (UI, logging)
                logger.warning(
                    f"Listener {type(listener).__name__}.{method_name} failed: {e}"
                )
```

### Structured error logging in DroidRun agent service

```python
# Source: pattern for replacing except Exception: pass in droidrun_agent_service.py

# BEFORE (line 91):
#   except Exception:
#       # Avoid log recursion on failures
#       pass

# AFTER:
except Exception as e:
    # Log the failure but avoid recursion by not re-emitting
    logger.error(f"DroidRunLogHandler emit failed: {e}", exc_info=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare `except: pass` | Typed exception hierarchy with structured context | This phase | Every error becomes observable and classifiable |
| Generic `Exception` in logs | `CrawlerError.to_log_dict()` with run/step/device context | This phase | Error entries are machine-parseable |
| Silent recorder failures | Fail-closed `RecorderError` on write failures | This phase | Data integrity guaranteed |

**Deprecated/outdated:**
- `except Exception: pass` in crawl-critical paths: being replaced entirely this phase
- `except:` bare except in report_generator.py:138: should be `except (json.JSONDecodeError, ValueError):` but is out of scope for this phase (report parsing, not crawl-critical)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Retry logic (tenacity or equivalent) is deferred to Phase 2+ | Architecture Patterns | If Phase 1 needs retry, scope expands significantly |
| A2 | Pydantic is overkill for exception context payloads | Alternatives Considered | If team prefers pydantic, adds dependency but no functional risk |
| A3 | UI/logging listener failures should NOT halt the run | Pitfalls 1, 3 | If operators want strict error visibility, may need to make these configurable |
| A4 | The `on_error` listener signature can remain unchanged if we pass `CrawlerError` instances | Pitfall 2 | If listeners inspect `error` type attributes, they may need updates |
| A5 | The `database.py:305` migration catch can be narrowed to `sqlite3.OperationalError` safely | Pitfall 5 | If other exception types occur during migration, they would no longer be silenced |

## Open Questions

1. **Should `DroidRunLogHandler.emit` (droidrun_agent_service.py:76-93) remain a defensive catch?**
   - What we know: It writes to a JSONL file and calls `_emit_event`. A failure here could cause infinite recursion if the error path triggers another log.
   - What's unclear: Whether there is a real recursion risk or it is theoretical.
   - Recommendation: Keep the catch but log the error instead of bare `pass`. This is a logging infrastructure handler, not a crawl-critical path.

2. **Should `_initialize_omni_parser` (droidrun_agent_service.py:289-305) failure be fatal or degraded?**
   - What we know: Current code catches the failure, logs a warning, and sets clients to None. Crawl continues without OmniParser.
   - What's unclear: Whether OmniParser is essential for DroidRun operation.
   - Recommendation: Keep as degraded mode (warning + None). OmniParser is optional enhancement, not crawl-critical.

3. **Should `crawl_state_machine.py:97` listener exception catch be modified?**
   - What we know: State machine catches listener exceptions with `except Exception: pass`. This is a UI notification path.
   - Recommendation: Keep the catch but log the exception. State machine listener failures should not break transitions.

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified -- this phase is pure code/config changes using only Python stdlib)

## Validation Architecture

> nyquist_validation is explicitly `false` in `.planning/config.json`. Skipping validation architecture section.

## Security Domain

> security_enforcement is not set in config.json (absent), so it defaults to enabled. However, this phase is about error handling taxonomy, not security features. The security implications are minimal.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | N/A -- not changing auth flows |
| V3 Session Management | no | N/A -- not changing session management |
| V4 Access Control | no | N/A -- not changing access control |
| V5 Input Validation | no | N/A -- not changing input validation |
| V6 Cryptography | no | N/A -- not changing cryptography |
| V10 Error Handling | yes | Typed exception taxonomy prevents information leakage through generic error messages |

### Known Threat Patterns for Error Handling

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Information disclosure via stack traces | Information Disclosure | `CrawlerError.to_log_dict()` controls what is logged; avoid exposing internal paths to UI |
| Denial of service via error flooding | Denial of Service | Structured logging with severity allows rate-limiting error output |

## Sources

### Primary (HIGH confidence)
- Codebase analysis: 28 bare `except Exception:` + 1 bare `except:` blocks found via grep [VERIFIED: codebase grep]
- crawler_loop.py: Full file read, all error paths identified [VERIFIED: file read]
- droidrun_agent_service.py: Full file read, all error paths identified [VERIFIED: file read]
- database.py: Full file read, migrate_schema blanket catch at line 305 [VERIFIED: file read]
- CONCERNS.md: Error suppression documented as tech debt item [VERIFIED: file read]
- PITFALLS.md: Pitfall 2 "Silent failures in core loop" documented [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- Python exception design patterns: hierarchy + chaining with `raise X from Y` [ASSUMED: training knowledge]
- Fail-closed design: standard pattern for persistent systems [ASSUMED: training knowledge]

### Tertiary (LOW confidence)
- None -- all findings are based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all stdlib
- Architecture: HIGH - direct codebase analysis of existing patterns and exception sites
- Pitfalls: HIGH - identified from actual codebase locations with line numbers

**Research date:** 2026-05-01
**Valid until:** 2026-06-01 (stable -- no external dependencies, codebase-driven)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ERRO-01 | All critical-path exceptions use typed taxonomy (retryable, fatal, operator-actionable) -- no bare `except: pass` | Typed exception hierarchy pattern with `CrawlerError` base + `RetryableError`, `FatalError`, `OperatorActionableError` subclasses. 28 blanket handlers identified for replacement in crawl-critical paths. |
| ERRO-02 | Error logs include structured context (run_id, step_id, action type, device state) for every failure | `ErrorContext` dataclass pattern with `to_dict()` for structured logging. `CrawlerError.to_log_dict()` provides machine-parseable error entries. |
| ERRO-03 | Recorder and checkpoint failures halt the run (fail-closed) rather than continuing silently | `RecorderError` and `CheckpointError` (both `FatalError` subclasses) raised from repository write methods. `_emit_event` modified to re-raise recorder errors. |
| ERRO-04 | Existing blanket exception handlers in crawl loop are replaced with typed handling | All blanket handlers mapped: crawler_loop.py:285, droidrun_agent_service.py:91/170/394/733, database.py:305. Each has specific replacement strategy documented. |
</phase_requirements>

## Blanket Handler Inventory

Complete list of `except Exception:` and `except:` blocks in crawl-critical code, with replacement strategy:

### Core (crawl loop)

| File | Line | Current Code | Replacement Strategy |
|------|------|-------------|---------------------|
| crawler_loop.py | 285 | `except Exception: continue` in `_emit_event` | Re-raise `RecorderError`/`CheckpointError`; log+continue for other listener failures |
| crawl_state_machine.py | 97 | `except Exception: pass` in `_notify_listeners` | Log warning + continue (UI notification, not critical) |
| crawl_controller.py | 146 | `except Exception as e:` in `_notify_state_change` | Already logs; acceptable as-is (UI notification) |
| log_sinks.py | 183/209/220/227/236 | Multiple `except Exception:` in stream capture | Keep defensive catches (logging infrastructure) but log the errors |
| logging_service.py | 31 | `except Exception as e:` in `log()` | Keep (already logs to stderr as fallback) |

### Domain (DroidRun agent)

| File | Line | Current Code | Replacement Strategy |
|------|------|-------------|---------------------|
| droidrun_agent_service.py | 91 | `except Exception: pass` in `DroidRunLogHandler.emit` | Log error instead of bare pass (avoid recursion) |
| droidrun_agent_service.py | 170 | `except Exception:` in `resolve_api_key` | Narrow to expected exceptions (KeyError, AttributeError) or log warning |
| droidrun_agent_service.py | 285 | `except Exception as e:` in `_initialize_agent` | Re-raise as `FatalError` (agent init failure is fatal) |
| droidrun_agent_service.py | 302 | `except Exception as e:` in `_initialize_omni_parser` | Keep as degraded (OmniParser is optional), already logs warning |
| droidrun_agent_service.py | 394 | `except Exception:` for WorkflowHandler import | Narrow to `ImportError` (expected when submodule absent) |
| droidrun_agent_service.py | 510 | `except Exception as e:` in `execute_exploration_task` | Wrap in typed exception with context; re-raise fatal errors |
| droidrun_agent_service.py | 647 | `except Exception as e:` in `_log_agent_interaction` | Log warning (degraded: failed to log, not critical) |
| droidrun_agent_service.py | 706 | `except Exception as e:` in `convert_droidrun_actions` | Log warning + continue (per-action conversion, not critical) |
| droidrun_agent_service.py | 719 | `except Exception as e:` in `cleanup` | Log warning (cleanup failure should not raise) |
| droidrun_agent_service.py | 733 | `except Exception: pass` in `cleanup` agent null-out | Log warning instead of bare pass |
| droidrun_agent_service.py | 787 | `except Exception as e:` in `_close_google_genai_client` | Log warning (resource cleanup) |
| droidrun_agent_service.py | 809 | `except Exception as e:` in `_shutdown_active_workflow` | Log warning (shutdown failure) |
| droidrun_agent_service.py | 853 | `except Exception as e:` in `analyze_ui_context` | Log warning + return empty (optional feature) |

### Infrastructure (database)

| File | Line | Current Code | Replacement Strategy |
|------|------|-------------|---------------------|
| database.py | 305 | `except Exception: pass` in `migrate_schema` | Narrow to `sqlite3.OperationalError` and log warning |
| run_repository.py | (all write methods) | No error handling at all | Add try/except raising `RecorderError` on write failures |
