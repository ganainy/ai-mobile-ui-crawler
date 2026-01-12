# Research Plan: OCR + Set-of-Mark Grounding

**Feature**: `009-ocr-som-grounding`
**Date**: 2026-01-12

## Decisions & Rationale

### 1. OCR Engine Selection
- **Decision**: Use `EasyOCR`.
- **Rationale**:
  - Better out-of-the-box support for multiple languages and scene text compared to Tesseract.
  - Returns bounding boxes directly.
  - Pure Python packaging (easier cross-platform install than Tesseract binaries).
  - Performance is acceptable on CPU for reasonable image sizes.
- **Alternatives Considered**:
  - `Tesseract`: Requires separate binary installation, tricky on Windows/CI.
  - `PaddleOCR`: Heavyweight, complex dependencies.
  - `Cloud Vision API`: Breaks "local-only" constraint, adds cost.

### 2. Set-of-Mark Overlay Strategy
- **Decision**: Use `Pillow` (PIL) to draw semi-transparent bounding boxes with high-contrast numeric labels.
- **Rationale**:
  - Standard, lightweight Python imaging library.
  - Fast enough for standard screenshot resolutions.
  - Full control over color, font, and opacity.
- **Alternatives Considered**:
  - `OpenCV`: Good for image processing, but text drawing API is limited (fonts, transparency) compared to PIL.

## Research Findings

### EasyOCR Performance
- **Validation**: Need to verify `EasyOCR` latency on a typical mobile screenshot (1080x2400).
- **Optimization**: Can reduce image resolution or use "fast" mode if latency > 2s.

## Pending Questions

- None.
