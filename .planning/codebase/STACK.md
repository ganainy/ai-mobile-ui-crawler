# Technology Stack

**Analysis Date:** 2026-04-05

## Languages

**Primary:**
- Python 3.9+ - Core application logic, GUI, AI integration, mobile automation
- JavaScript/TypeScript - DroidRun agent system (external dependency)

**Secondary:**
- QML - UI definition (PySide6/PyQt6 integration)
- SQL - Database queries

## Runtime

**Environment:**
- Python 3.9+ (support for 3.9, 3.10, 3.11, 3.12)
- Windows 11 Pro 10.0.26200
- Shell: bash (via Git)

**Package Manager:**
- pip - Primary package manager
- setuptools - Build system
- Lockfile: Not detected (using standard pip/PyPI)

## Frameworks

**Core:**
- PySide6 6.6.0+ - Main UI framework
- Appium 3.0.0+ - Mobile device automation
- Qt 6 - GUI framework foundation

**Testing:**
- pytest 7.0.0+ - Test runner
- pytest-cov 4.0.0+ - Coverage reporting
- pytest-qt 4.0.0+ - Qt widget testing

**Build/Dev:**
- ruff 0.1.0+ - Linter and formatter
- black 23.0.0+ - Code formatter
- pre-commit 3.0.0+ - Git hooks

## Key Dependencies

**Critical:**
- appium-python-client 3.0.0+ - Mobile automation driver
- Pillow 10.0.0+ - Image processing for screenshots
- cryptography 42.0.0+ - Secure configuration and encryption
- requests 2.31.0+ - HTTP requests for AI APIs
- click 8.1.0+ - CLI interface

**AI/ML:**
- google-genai 0.3.0+ - Gemini AI integration
- ollama 0.2.0+ - Local LLM support
- pytesseract 0.3.10+ - OCR text recognition
- easyocr 1.7.0+ - Alternative OCR engine
- imagehash 4.3.0+ - Image similarity detection

**UI/UX:**
- PySide6 6.6.0+ - Main Qt bindings
- reportlab 4.0.0+ - PDF report generation
- pyyaml 6.0.0+ - Configuration file parsing

**Infrastructure:**
- psutil 5.9.0+ - System monitoring
- sqlite3 - Built-in database support

## Configuration

**Environment:**
- Configuration via `pyproject.toml` for project metadata
- Environment variables for API keys (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)
- User configuration stored in app data directory
- Secrets managed via `CredentialStore` with encryption

**Build:**
- setuptools as build backend
- Package structure: `src/` directory layout
- Entry points: `mobile-crawler-cli` and `mobile-crawler-gui`

## Platform Requirements

**Development:**
- Python 3.9+
- pip
- Node.js (npm/npx) - for DroidRun development
- Docker Desktop - for containerized environments

**Production:**
- Python 3.9+ runtime
- ADB (Android Debug Bridge) - for device communication
- Appium server (can be remote)
- Optional: Local Ollama server for offline AI

---

*Stack analysis: 2026-04-05*