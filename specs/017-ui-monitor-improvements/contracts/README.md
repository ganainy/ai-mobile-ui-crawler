# Contracts: UI Monitor Improvements

**Feature**: 017-ui-monitor-improvements  
**Date**: 2026-01-14

## Overview

This feature is **UI-only** and does not introduce new API contracts. All changes are internal to the Qt widget layer.

## Internal Interfaces

The following internal Python interfaces are affected:

### AIMonitorPanel Methods

```python
class AIMonitorPanel(QWidget):
    def add_request(self, run_id: int, step_number: int, request_data: dict) -> None:
        """Add a pending AI request to the monitor."""
        pass
    
    def add_response(self, run_id: int, step_number: int, response_data: dict) -> None:
        """Complete an AI interaction with response data.
        
        Note: Will ignore duplicate calls if _response_updated flag is set.
        """
        pass
```

### JsonTreeWidget Interface (NEW)

```python
class JsonTreeWidget(QTreeWidget):
    def __init__(self, data: Union[dict, list, str], parent: Optional[QWidget] = None):
        """Create a collapsible JSON tree widget.
        
        Args:
            data: JSON data as dict, list, or JSON string
            parent: Optional parent widget
        """
        pass
    
    def collapse_to_root(self) -> None:
        """Collapse all items except root level."""
        pass
    
    def set_data(self, data: Union[dict, list, str]) -> None:
        """Update the displayed data."""
        pass
```

## Signal Contracts (Existing)

No changes to Qt signals. The existing signal signatures remain:

```python
# In signal_adapter.py
ai_request_sent = Signal(int, int, dict)      # run_id, step_number, request_data
ai_response_received = Signal(int, int, dict) # run_id, step_number, response_data
```

## Notes

For REST/GraphQL API contracts, this feature has no external-facing endpoints. All functionality is contained within the Qt UI layer.
