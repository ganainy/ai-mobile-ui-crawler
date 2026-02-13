# Quickstart: Grounding Module

## Installation

Ensure `EasyOCR` is installed (it may require PyTorch):

```bash
pip install easyocr
```

## Usage

```python
from mobile_crawler.domain.grounding import GroundingManager

grounding = GroundingManager()
raw_screenshot = "screenshots/home.png"

# Process screenshot to get marked image + label map
result = grounding.process_screenshot(raw_screenshot)

print(f"Marked image saved to: {result.marked_image_path}")
print(f"Detected {len(result.label_map)} interactive text elements.")

# If AI says "Click label 5":
coords = result.label_map.get(5)
if coords:
    print(f"Clicking at {coords}")
else:
    print("Invalid label")
```
