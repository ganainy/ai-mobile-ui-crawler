# API Contracts: Crawl Stability & Observability Fixes

**Branch**: `024-crawl-stability-fixes` | **Date**: 2026-01-15

## Overview

This feature is primarily internal bug fixes and doesn't introduce new public APIs. This document describes the minimal contract changes for internal interfaces.

---

## Internal Event Contract Updates

### CrawlerEventListener.on_crawl_completed

**Current Signature**:
```python
def on_crawl_completed(
    self, 
    run_id: int, 
    total_steps: int, 
    duration_ms: float, 
    reason: str
) -> None:
    pass
```

**Extended Data** (via extra parameter or existing pattern):
```python
# Option 1: Extended signature (breaking change - not recommended)
def on_crawl_completed(
    self, 
    run_id: int, 
    total_steps: int, 
    duration_ms: float, 
    reason: str,
    stats: Optional[Dict[str, Any]] = None  # OCR stats, etc.
) -> None:
    pass

# Option 2: Use existing event system with extra_data (recommended)
# Stats passed through existing event emission mechanism
```

**Stats Dictionary Schema**:
```json
{
  "ocr_avg_time_ms": 245.5,
  "ocr_total_operations": 12,
  "paused_duration_ms": 15000,
  "recovery_count": 0,
  "recovery_time_ms": 0
}
```

---

## Configuration Contract

### New Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mobsf_request_timeout` | `integer` | `300` | HTTP request timeout in seconds for MobSF API calls |

### Existing Keys (no changes)

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `mobsf_scan_timeout` | `integer` | `900` | Total scan wait timeout |
| `mobsf_poll_interval` | `float` | `2.0` | Polling interval |
| `enable_traffic_capture` | `boolean` | `false` | PCAPdroid enable flag |
| `max_crawl_duration_seconds` | `integer` | `600` | Time-based crawl limit |
| `max_crawl_steps` | `integer` | `15` | Step-based crawl limit |

---

## No External API Changes

This feature does not modify:
- CLI command interfaces
- REST/HTTP endpoints (if any)
- Database schema
- File format specifications
