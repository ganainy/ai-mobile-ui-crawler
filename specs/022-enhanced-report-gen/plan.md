# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The goal is to implement a comprehensive report generation feature that aggregates crawl run data (screenshots, actions), security findings (MobSF), and network traffic (PCAP) into a single, printer-friendly HTML report. This report is critical for the user's master thesis and must provide enriched context by correlating user actions with network events.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: 
- `jinja2` (HTML templating)
- `scapy` or `dpkt` (PCAP parsing)
- `pandas` (optional, for timeline correlation if complex)
**Storage**: File system (JSON inputs, HTML output, PCAP files)
**Testing**: `pytest`
**Target Platform**: Windows (User's OS), Desktop App
**Project Type**: Single python package (`src/mobile_crawler`)
**Performance Goals**: Generate report in < 30s. Handle PCAP files ~10-50MB.
**Constraints**: 
- Must work with existing run artifacts structure.
- Must gracefully handle missing inputs (e.g. no MobSF report).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principles Checked**:
- **Simplicity**: Using standard HTML/Jinja2 avoids complex PDF generation dependencies.
- **Test-First**: Will define contracts for parsers and generators.
- **Integration**: Depends on MobSF/PCAP existing outputs.

**Status**: PASS (No blockers identified in empty constitution).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── reporting/                 # NEW MODULE
│   ├── contracts.py           # (Moved from specs or imported)
│   ├── generator.py           # ReportGenerator implementation
│   ├── correlator.py          # Logic to merge steps + traffic
│   ├── parsers/
│   │   ├── pcap_parser.py     # dpkt implementation
│   │   └── mobsf_parser.py    # JSON parser
│   └── templates/
│       └── report.html.j2     # Jinja2 template
```

**Structure Decision**: A dedicated `reporting` package within the main library to encapsulate all report generation logic. Parsers are separated to allow easy swapping (e.g. if we switch from dpkt to scapy). Termplates are stored within the package.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
