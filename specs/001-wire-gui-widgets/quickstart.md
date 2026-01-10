# Quickstart: Wire Up GUI Widgets

**Feature**: 001-wire-gui-widgets  
**Date**: 2026-01-10

## Running the GUI

### Prerequisites

1. **Python Environment**
   ```bash
   cd mobile-crawler
   pip install -e .
   ```

2. **Android Device**
   - Connect device via USB
   - Enable USB debugging
   - Verify with: `adb devices`

3. **Appium Server**
   ```bash
   npx appium -p 4723 --relaxed-security
   ```

4. **AI Provider API Key**
   - Gemini: Get from https://aistudio.google.com/
   - OpenRouter: Get from https://openrouter.ai/
   - Ollama: Run local Ollama server

### Launch GUI

```bash
# Using entry point
mobile-crawler-gui

# Or directly
python -c "from mobile_crawler.ui.main_window import run; run()"
```

### First Crawl Workflow

1. **Configure AI Provider**
   - Select provider from dropdown (e.g., "Gemini")
   - Enter API key in Settings panel
   - Wait for model list to populate
   - Select a vision-capable model

2. **Select Device**
   - Click "Refresh" in Device Selector
   - Select your connected device

3. **Select Target App**
   - Choose an installed app from the dropdown
   - Or enter package name manually

4. **Start Crawl**
   - Click "Start Crawl" button
   - Watch logs appear in Log Viewer
   - Monitor progress in Stats Dashboard

5. **Control Crawl**
   - Click "Pause" to pause
   - Click "Resume" to continue
   - Click "Stop" to end crawl

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No devices found | Check USB connection, enable USB debugging |
| Appium connection failed | Ensure Appium server is running on port 4723 |
| AI API error | Verify API key is correct and has quota |
| App not launching | Ensure package name is correct |
