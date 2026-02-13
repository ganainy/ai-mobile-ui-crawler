# Data Model

## Core Entities

### 1. Screen
Represents a unique state of the application UI.

- **id**: `string` (Hash of the perceptual hash of the screenshot)
- **hash**: `string` (dhash/phash of the screenshot image)
- **screenshot_path**: `string` (Path to the stored image file)
- **discovered_at**: `datetime`
- **visit_count**: `integer`

*Note: No `xml_source` or `view_hierarchy` fields.*

### 2. Action
Represents an interaction performed on the device.

- **type**: `enum` (click, input, scroll_*, back, long_press)
- **coordinates**: `Box` {top_left: [x,y], bottom_right: [x,y]}
- **input_text**: `string` (Optional, only for input type)
- **reasoning**: `string` (AI justification)

## Helper Types

### BoundingBox
- **top_left**: `[x, y]`
- **bottom_right**: `[x, y]`

## Storage Schema (SQLite)

### runs
- `id`: INTEGER PK
- `app_package`: TEXT
- `start_time`: DATETIME
- `status`: TEXT
- `total_steps`: INTEGER
- `unique_screens`: INTEGER

### step_logs
- `id`: INTEGER PK
- `run_id`: INTEGER FK
- `step_number`: INTEGER
- `from_screen_id`: INTEGER FK (Refers to screen hash/id)
- `to_screen_id`: INTEGER FK
- `action_type`: TEXT
- `target_bbox_json`: TEXT (JSON string of coordinates)
- `input_text`: TEXT
- `ai_response_time_ms`: FLOAT
- `execution_success`: BOOLEAN
