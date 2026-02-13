# Research: Enhanced Report Generation

**Feature**: Enhanced Report Generation
**Date**: 2026-01-15

## Unknowns & Decisions

### 1. PCAP Parsing Library
**Decision**: Use **dpkt**.
**Rationale**: 
- `dpkt` is pure Python, fast, and does not require external binary dependencies like Wireshark (unlike `pyshark`).
- `scapy` is powerful but can be slow for reading large files and has a heavier footprint.
- We only need read-only access to extract HTTP headers and timestamps, which `dpkt` handles efficiently.

### 2. HTML Templating
**Decision**: Use **Jinja2**.
**Rationale**:
- Standard in Python ecosystem.
- Powerful inheritance and macro support for creating modular report sections (Summary, Timeline, Security).
- Easy to pass Python objects directly to the template.

### 3. Data Correlation Strategy
**Decision**: Time-window matching.
**Rationale**:
- Run data (screenshots/actions) has timestamps.
- PCAP packets have timestamps.
- We will group network requests that occur between `Step N Start Time` and `Step N+1 Start Time` (or End Time).
- A specialized helper class `RunCorrelator` will build this structure before passing to the template.

### 4. Report Styling
**Decision**: Embedded CSS in single HTML file.
**Rationale**:
- Ensures the report is portable (one file to share/submit).
- CSS framework: Minimal custom CSS or a lightweight CDN-free snippet (e.g. Simple.css or custom flexbox) to ensure it works offline.
