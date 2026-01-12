# Data Model: OCR + Set-of-Mark

## Entities

### `OCRResult`
Represents a single text element detected on the screen.

```python
@dataclass
class OCRResult:
    text: str
    box: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    confidence: float
    center: Tuple[int, int]  # Derived: ((x1+x2)/2, (y1+y2)/2)
```

### `GroundingOverlay`
Represents the result of the grounding process, containing the marked image and the mapping for interaction.

```python
@dataclass
class GroundingOverlay:
    marked_image_path: str
    label_map: Dict[int, Tuple[int, int]]  # Label_ID -> (x, y) center coordinates
    original_dimensions: Tuple[int, int]
```

## Contracts / Interfaces

### `OCREngine` Protocol

```python
class OCREngine(Protocol):
    def detect_text(self, image_path: str) -> List[OCRResult]:
        """
        Detects text in the given image.
        """
        ...
```

### `GroundingManager`

```python
class GroundingManager:
    def process_screenshot(self, screenshot_path: str) -> GroundingOverlay:
        """
        1. Runs OCREngine.detect_text()
        2. Assigns numeric labels to results
        3. Draws overlays using PIL
        4. Returns GroundingOverlay with label->coord map
        """
        ...
```
