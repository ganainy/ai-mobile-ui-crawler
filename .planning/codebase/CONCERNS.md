# Codebase Concerns

**Analysis Date:** 2026-04-05

## Tech Debt

**Screen Change Detection:**
- Issue: Navigation tracking incomplete, important for crawler state management
- Files: `src/mobile_crawler/domain/action_executor.py:122`
- Impact: Crawler may lose track of app navigation state
- Fix approach: Implement screen change detection using UI hierarchy comparison or accessibility events

**Exception Handling:**
- Issue: Bare except clause catches all exceptions without specific handling
- Files: `src/mobile_crawler/domain/report_generator.py:138`
- Impact: Poor error tracking and debugging capabilities
- Fix approach: Replace with specific exception types and proper error handling

**Logging Implementation:**
- Issue: excessive debug logging in production codebase
- Files: `src/mobile_crawler/infrastructure/appium_driver.py` (multiple debug logs)
- Impact: Performance degradation and noise in production logs
- Fix approach: Use appropriate log levels and conditionally debug logging based on environment

## Known Bugs

**Screen Recording Reliability:**
- Symptoms: Video recording may fail silently or produce empty files
- Files: `src/mobile_crawler/infrastructure/appium_driver.py:575-617`
- Trigger: Appium session instability or device limitations
- Workaround: Check return values and implement retry logic

**State Management Inconsistencies:**
- Symptoms: App context may not be properly maintained between actions
- Files: `src/mobile_crawler/domain/app_context_manager.py:89,109,138`
- Trigger: Multiple rapid actions or app switches
- Workaround: Implement proper state validation and recovery

## Security Considerations

**Subprocess Command Injection:**
- Risk: Potential command injection through unsanitized inputs
- Files: Multiple files using `subprocess.run()` with user input
- Current mitigation: Basic input sanitization in some areas
- Recommendations: Implement parameterized commands and input validation

**Configuration Security:**
- Risk: Sensitive data stored in SQLite without encryption
- Files: `src/mobile_crawler/config/config_manager.py`
- Current mitigation: Environment variable support for secrets
- Recommendations: Implement encryption for sensitive configuration values

**External Service Dependencies:**
- Risk: Dependency on external services (Mailosaur, PCAPdroid) without proper validation
- Files: `src/mobile_crawler/infrastructure/mailosaur/service.py`, `src/mobile_crawler/domain/traffic_capture_manager.py`
- Current mitigation: Basic permission checks
- Recommendations: Implement service health checks and fallback mechanisms

## Performance Bottlenecks

**Large Resource File:**
- Problem: UI resource file is extremely large (3795 lines)
- Files: `src/mobile_crawler/ui/resources/resources_rc.py`
- Cause: Auto-generated Qt resources
- Improvement path: Optimize resource generation or split into multiple files

**Synchronous Operations:**
- Problem: Some async operations use blocking calls
- Files: `src/mobile_crawler/infrastructure/adb_client.py:92`
- Cause: Backward compatibility requirements
- Improvement path: Migrate fully to async patterns where possible

**Action Delays:**
- Problem: Fixed 2-second delays between actions may be too long
- Files: `src/mobile_crawler/domain/action_executor.py:42`
- Cause: Visual observability requirement
- Improvement path: Make delay configurable and adaptive based on action type

## Fragile Areas

**Appium Session Management:**
- Files: `src/mobile_crawler/infrastructure/appium_driver.py`
- Why fragile: Appium sessions can be lost unexpectedly
- Safe modification: Implement session health checks and auto-reconnection
- Test coverage: Needs better session loss recovery tests

**ADB Command Execution:**
- Files: `src/mobile_crawler/infrastructure/adb_client.py`
- Why fragile: Device connectivity issues and command timeouts
- Safe modification: Implement exponential backoff for retries
- Test coverage: Limited error scenario testing

**Configuration Loading:**
- Files: `src/mobile_crawler/config/config_manager.py:44-48`
- Why fragile: Database access failures can cascade
- Safe modification: Implement graceful fallback mechanisms
- Test coverage: Missing database failure scenarios

## Scaling Limits

**Memory Usage:**
- Current capacity: Unknown, likely limited by Appium and device capabilities
- Limit: Large numbers of simultaneous crawls may exhaust device resources
- Scaling path: Implement per-device resource monitoring and limits

**Database Size:**
- Current capacity: SQLite without size optimization
- Limit: May become slow with many crawl runs
- Scaling path: Implement data pruning and index optimization

**Concurrent Crawls:**
- Current capacity: Single process design
- Limit: Cannot crawl multiple devices simultaneously
- Scaling path: Refactor to async event-driven architecture

## Dependencies at Risk

**Appium:**
- Risk: Version compatibility issues
- Impact: Core functionality dependent
- Migration plan: Pin to specific stable version with testing

**PyQt/PySide:**
- Risk: GUI framework version updates
- Impact: UI may break with major version changes
- Migration plan: Test compatibility before upgrades

## Missing Critical Features

**Network Traffic Analysis:**
- Problem: Basic PCAP capture but no analysis
- Blocks: Security testing and network behavior understanding
- Priority: High for security-focused crawling

**Test Automation Framework:**
- Problem: Limited automated testing
- Blocks: CI/CD pipeline reliability
- Priority: High for maintainability

## Test Coverage Gaps

**Error Scenarios:**
- What's not tested: Device disconnection, Appium session loss
- Files: Core infrastructure modules
- Risk: Silent failures in production
- Priority: High

**Configuration Edge Cases:**
- What's not tested: Invalid configurations, missing settings
- Files: Configuration management modules
- Risk: Runtime crashes on invalid input
- Priority: Medium

*Concerns audit: 2026-04-05*
