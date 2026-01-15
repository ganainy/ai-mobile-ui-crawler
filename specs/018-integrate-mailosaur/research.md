# Research: Integrate Mailosaur Service

**Feature**: Integrate Mailosaur Service
**Date**: 2026-01-15

## Unknowns & Clarifications

### 1. Mailosaur Python SDK
**Task**: Identify the official Python SDK and its capabilities.
**Decision**: Use `mailosaur` package.
**Rationale**: Official SDK provided by Mailosaur.
**Alternatives**: Direct HTTP requests (rejected for convenience of SDK).

### 2. Message Retrieval Strategy
**Task**: Determine how to efficiently wait for and retrieve specific messages.
**Decision**: Use `MeshageResource.get()` which polls/waits for a message matching criteria.
**Rationale**: Standard pattern in Mailosaur SDK to avoid manual polling loops.

## Technology Choices

| generic | Chosen | Rationale |
|---------|--------|-----------|
| Library | `mailosaur` | Official SDK |
| Async/Sync | Sync | `mailosaur` SDK is synchronous. Crawler is likely running in a thread or can block for this operation. |

## Implementation Details

- **Dependencies**: Add `mailosaur` to `requirements.txt` or `pyproject.toml`.
- **Configuration**: Needs `MAILOSAUR_API_KEY` and `MAILOSAUR_SERVER_ID` env vars.
