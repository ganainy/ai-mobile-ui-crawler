# Quickstart: Mobile Crawler GUI

**Feature**: 001-wire-gui-widgets  
**Date**: 2026-01-10
**Status**: ✅ Complete - GUI fully functional with comprehensive error handling

## Running the GUI

### Prerequisites

1. **Python Environment**
   ```bash
   cd mobile-crawler
   pip install -e .
   ```

2. **Android Device or Emulator**
   - Connect Android device via USB, OR
   - Start Android emulator (e.g., Android Studio AVD)
   - Enable USB debugging in developer options
   - Verify connection: `adb devices`

3. **Appium Server**
   ```bash
   npx appium -p 4723 --relaxed-security
   ```
   Keep this running in a separate terminal.

4. **AI Provider Setup**
   - **Gemini**: Get API key from https://aistudio.google.com/
   - **OpenRouter**: Get API key from https://openrouter.ai/
   - **Ollama**: Install and run local Ollama server

### Launch GUI

```bash
# Using entry point
mobile-crawler-gui

# Or directly
python -c "from mobile_crawler.ui.main_window import run; run()"
```

## Complete Usage Workflow

### 1. Initial Setup

1. **Launch the application** - GUI opens with main window
2. **Configure AI Provider** (required first):
   - Open Settings panel (right side)
   - Select AI provider tab
   - Enter your API key
   - Click "Save Settings"
   - Select provider and model from AI Model Selector

### 2. Device Connection

1. **Connect Android device** or start emulator
2. **In Device Selector** (left panel):
   - Click "Refresh" button
   - Select your device from dropdown
   - If no devices found, check USB connection and try again

### 3. App Selection

1. **In App Selector** (left panel):
   - Click "List Apps" to see installed apps, OR
   - Enter package name manually (e.g., `com.example.app`)
   - Select target app for crawling

### 4. Start Crawling

1. **Click "Start Crawl"** button (center panel)
2. **Monitor progress**:
   - Real-time logs in Log Viewer (right panel)
   - Statistics in Stats Dashboard (center panel)
   - Crawl state in Control Panel

### 5. Control Operations

- **Pause**: Temporarily stop crawling
- **Resume**: Continue from where paused
- **Stop**: End crawl completely
- **View History**: Check past crawls in bottom panel

## Error Handling

The application provides helpful error dialogs for common issues:

### No Devices Found
- **Dialog**: Explains USB debugging setup
- **Solution**: Check device connection, enable debugging, try "Refresh"

### Appium Not Running
- **Dialog**: Instructions to start Appium server
- **Solution**: Run `npx appium -p 4723 --relaxed-security`

### Invalid API Key
- **Dialog**: Format validation warnings
- **Solution**: Check API key in Settings, ensure correct format

### Configuration Incomplete
- **Dialog**: Clear messages for missing device/app/AI setup
- **Solution**: Complete all required selections before starting

## Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| No devices found | "No devices available" in device selector | Check USB connection, enable USB debugging, accept authorization prompt |
| Appium connection failed | Error when listing apps | Ensure Appium server is running: `npx appium -p 4723 --relaxed-security` |
| Invalid API key | Settings save warning | Verify API key format and length, check provider dashboard for validity |
| App not found | Package name validation error | Use "List Apps" button or verify package name format |
| Crawl won't start | Start button disabled | Ensure device, app, and AI provider are all configured |

## Advanced Usage

- **Custom System Prompts**: Configure in Settings for specialized crawling behavior
- **Crawl Limits**: Set max steps and duration in Settings
- **Test Credentials**: Configure login credentials for apps that require authentication
- **Run History**: Review past crawls with detailed statistics and reports
