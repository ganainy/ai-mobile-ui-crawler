"""Collapsible tree widget for displaying JSON data."""

import json
from typing import Any, List, Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget


class JsonTreeWidget(QTreeWidget):
    """Collapsible tree widget for displaying JSON data."""

    def __init__(self, data: Union[dict, list, str], parent: Optional[QWidget] = None):
        """
        Args:
            data: JSON data as dict, list, or JSON string
            parent: Parent widget
        """
        super().__init__(parent)
        self.setHeaderLabels(["Key", "Value"])
        self.setColumnCount(2)
        self.setAlternatingRowColors(True)
        
        # Set dark theme styling
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3d3d3d;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: #e0e0e0;
                padding: 4px;
                border: 1px solid #2b2b2b;
            }
        """)

        # Process data
        parsed_data = self._parse_json(data)
        if parsed_data is not None:
            self._build_tree(parsed_data, self.invisibleRootItem())
        
        # Adjust column widths
        self.header().setStretchLastSection(True)
        self.setColumnWidth(0, 150)
        
        # Initially collapse to root level
        self.collapse_to_root()

    def _parse_json(self, data: Any) -> Any:
        """Parse input data into dict or list."""
        if isinstance(data, (dict, list)):
            return data
        
        if isinstance(data, str):
            # Strip markdown code fences if present
            cleaned = data.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                # Remove opening fence (```json or ```)
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove closing fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = '\n'.join(lines).strip()
            
            try:
                # First attempt
                parsed = json.loads(cleaned)
                # Handle double-encoded JSON strings
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass
                return parsed
            except (json.JSONDecodeError, TypeError):
                # Return data as-is if not valid JSON
                return data
        
        return data

    def _build_tree(self, data: Any, parent_item: QTreeWidgetItem, key: Optional[str] = None) -> None:
        """Recursively build tree items from JSON data."""
        if isinstance(data, dict):
            # Create item for the dictionary itself if it's nested
            item = parent_item
            if key is not None:
                item = QTreeWidgetItem(parent_item)
                item.setText(0, str(key))
                item.setText(1, f"{{ {len(data)} keys }}")
            
            # Add child items for each key/value pair
            for k, v in data.items():
                self._build_tree(v, item, k)
                
        elif isinstance(data, list):
            # Create item for the list itself if it's nested
            item = parent_item
            if key is not None:
                item = QTreeWidgetItem(parent_item)
                item.setText(0, str(key))
                item.setText(1, f"[ {len(data)} items ]")
            
            # Add child items for each element
            for i, v in enumerate(data):
                self._build_tree(v, item, f"[{i}]")
                
        else:
            # Simple value
            item = QTreeWidgetItem(parent_item)
            item.setText(0, str(key) if key is not None else "")
            
            # Format value string
            val_str = str(data)
            # Truncate very long single values if needed
            if len(val_str) > 1000:
                val_str = val_str[:1000] + "..."
                
            item.setText(1, val_str)

    def collapse_to_root(self) -> None:
        """Collapse all items except root level."""
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            self._collapse_recursive(item)
            # Expand the root level items
            item.setExpanded(True)

    def _collapse_recursive(self, item: QTreeWidgetItem) -> None:
        """Recursively collapse an item and its children."""
        item.setExpanded(False)
        for i in range(item.childCount()):
            self._collapse_recursive(item.child(i))

    def set_data(self, data: Any) -> None:
        """Update the displayed data."""
        self.clear()
        parsed_data = self._parse_json(data)
        if parsed_data is not None:
            self._build_tree(parsed_data, self.invisibleRootItem())
        self.collapse_to_root()
