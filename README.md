# Mobile Crawler

AI-Powered Android Exploration Tool (Image-Only Mode)

## Overview

Mobile Crawler is an automated exploration tool for Android mobile applications using AI-driven **visual-only analysis** and intelligent action decisions. It operates in **image-only mode**, meaning it uses screenshots and coordinate-based actions without accessing XML page source or DOM hierarchy. The crawler captures screenshots, analyzes them via pluggable AI providers (VLM), translates analysis into device commands, and executes them via Appium.

## Features

- **Image-Only Operation**: Operates purely on visual feedback (screenshots) with coordinate-based actions - no XML/DOM access
- **AI-Driven Exploration**: Uses vision-capable AI models (Gemini, OpenRouter, Ollama) to analyze screenshots and determine next actions
- **Multiple Interfaces**: Both GUI and CLI interfaces for different use cases
- **Comprehensive Logging**: Detailed action logs, statistics, and reporting
- **Network Traffic Capture**: PCAPdroid integration for capturing network traffic during crawl sessions
- **Video Recording**: Automatic screen recording of crawl sessions using Appium's built-in recording
- **Security Analysis**: MobSF integration for static security analysis of Android applications
- **Flexible Configuration**: Environment variables, database settings, and user preferences with validation
- **Enhanced Reporting**: Generates human-readable HTML reports (printer-friendly) and machine-readable JSON reports with correlated timeline of actions and network requests

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd mobile-crawler

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.\.venv\Scripts\Activate.ps1

# Install project
pip install -e .

# Install development dependencies (optional)
pip install -e ".[dev]"
```

## Development Status

### ✅ Completed (Phase 0)
- Project structure and packaging
- Linting and formatting setup (Ruff, Black)
- Testing framework (pytest)
- Virtual environment isolation

### ✅ Completed (Phase 1 - Database Layer)
- **crawler.db schema**: Complete SQLite schema with 6 tables (runs, screens, step_logs, transitions, run_stats, ai_interactions)
- **user_config.db schema**: User preferences and encrypted secrets storage
- **Secrets encryption**: Fernet encryption with machine-bound key derivation for API keys
- **RunRepository**: Complete CRUD operations for runs table with cascading deletes
- Database connection management with WAL mode and foreign keys
- Comprehensive test coverage for all database operations

### ✅ Completed (Phase 2 - Image-Only Mode)
- **Image-Only Architecture**: Removed all XML/DOM access, now operates purely on screenshots and coordinates
- **ADB Text Input**: Implemented ADB-based text input handler to avoid DOM access
- **Coordinate-Based Actions**: All actions use visual coordinates from VLM, no element selectors
- **Updated Prompts**: System prompts explicitly request coordinate-based actions

### ✅ Completed (Phase 3 - Feature Integrations)
- **Traffic Capture**: PCAPdroid integration for network traffic analysis during crawl sessions
- **Video Recording**: Appium-based screen recording with automatic saving to session directories
- **MobSF Analysis**: Static security analysis with PDF/JSON report generation and security score tracking
- **Configuration Management**: UI and CLI configuration with validation and persistence
- **Prerequisite Validation**: Pre-crawl checks for feature dependencies (PCAPdroid, MobSF server, video support)
- **Graceful Degradation**: Crawl continues successfully even if optional features fail

### ✅ Completed (Phase 4 - Enhanced Reporting)
- **HTML/JSON Report Generator**: Transitioned from basic PDF to rich, printer-friendly HTML and structured JSON reports
- **Context-Enriched Timeline**: Correlates network requests (HTTP/DNS) from PCAP files with specific crawl steps based on timestamps
- **Integrated Analysis**: Aggregates MobSF security findings and network traffic summaries into a single unified report
- **Modular Reporting Architecture**: Decoupled parsers (PCAP, MobSF) and generators (Jinja2) for extensibility

## Usage

### CLI

Basic crawl:
```bash
mobile-crawler-cli crawl --package com.example.app --device emulator-5554 --model gemini-1.5-pro --provider gemini
```

With optional features:
```bash
# Enable traffic capture
mobile-crawler-cli crawl --package com.example.app --device emulator-5554 --model gemini-1.5-pro --provider gemini --enable-traffic-capture

# Enable video recording
mobile-crawler-cli crawl --package com.example.app --device emulator-5554 --model gemini-1.5-pro --provider gemini --enable-video-recording

# Enable MobSF analysis
mobile-crawler-cli crawl --package com.example.app --device emulator-5554 --model gemini-1.5-pro --provider gemini --enable-mobsf-analysis

# Enable all features
mobile-crawler-cli crawl --package com.example.app --device emulator-5554 --model gemini-1.5-pro --provider gemini --enable-traffic-capture --enable-video-recording --enable-mobsf-analysis
```

### GUI
```bash
mobile-crawler-gui
```

## Requirements

- Python 3.9+
- Android device or emulator
- Appium server
- AI provider API keys (Gemini, OpenRouter, or Ollama)

### Optional Requirements (for additional features)

- **PCAPdroid** (for traffic capture): Install from [F-Droid](https://f-droid.org/packages/com.emanuelef.remote_capture/)
- **MobSF Server** (for security analysis): Running MobSF instance with API access
- **ADB** (Android Debug Bridge): Required for PCAPdroid control and APK extraction

## Development

```bash
# Run tests
pytest

# Run linter
ruff check .

# Format code
black .

# Generate coverage report
pytest --cov=mobile_crawler --cov-report=html
```

## Project Structure

```
src/mobile_crawler/
├── core/              # Business logic and domain models
├── infrastructure/    # External services and persistence
├── domain/           # Use cases and business rules
├── ui/               # User interface components
├── cli/              # Command-line interface
├── config/           # Configuration management
└── utils/            # Utility functions

tests/                # Test suite
├── infrastructure/   # Infrastructure layer tests
└── ...

## Data Organization

The crawler organizes all session data into a unified directory structure for easy access and portability.

### Session Folder Structure
By default, all artifacts are stored in `output_data/` (or platform-specific AppData directory):

```text
output_data/run_{ID}_{TIMESTAMP}/
├── screenshots/      # All full and annotated screenshots
├── reports/          # PDF crawl reports and MobSF analysis results
└── data/             # JSON run exports and database snippets
```

Each run's `session_path` is persisted in the database, allowing the UI to open the correct folder directly.
```

## Database Schema

### crawler.db
- `runs` - Crawl session metadata
- `screens` - Discovered screen states with perceptual hashes
- `step_logs` - Per-step action history
- `transitions` - Screen-to-screen navigation graph
- `run_stats` - Comprehensive crawl statistics
- `ai_interactions` - AI request/response logging

### user_config.db
- `user_config` - Key-value user settings
- `secrets` - Encrypted API keys and credentials

## License

MIT