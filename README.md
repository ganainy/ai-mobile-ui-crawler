# Mobile Crawler

AI-Powered Android Exploration Tool (Image-Only Mode)

## Overview

Mobile Crawler is an automated exploration tool for Android mobile applications using AI-driven **visual-only analysis** and intelligent action decisions. It operates in **image-only mode**, meaning it uses screenshots and coordinate-based actions without accessing XML page source or DOM hierarchy. The crawler captures screenshots, analyzes them via pluggable AI providers (VLM), translates analysis into device commands, and executes them via Appium.

## Features

- **Image-Only Operation**: Operates purely on visual feedback (screenshots) with coordinate-based actions - no XML/DOM access
- **AI-Driven Exploration**: Uses vision-capable AI models (Gemini, OpenRouter, Ollama) to analyze screenshots and determine next actions
- **Multiple Interfaces**: Both GUI and CLI interfaces for different use cases
- **Comprehensive Logging**: Detailed action logs, statistics, and reporting
- **External Integrations**: PCAPdroid traffic capture, MobSF security analysis, video recording
- **Flexible Configuration**: Environment variables, database settings, and user preferences

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

### 🔄 In Progress
- Additional testing and validation of image-only mode

## Usage

### CLI
```bash
mobile-crawler-cli crawl --package com.example.app --device emulator-5554
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

output_data/          # Crawl session data (created at runtime)
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