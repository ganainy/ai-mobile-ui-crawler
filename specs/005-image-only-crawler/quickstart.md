# Quickstart: Image-Only Crawler

## Prerequisites

- **Appium Server**: Running on port 4723.
- **Android Emulator/Device**: Connected via ADB.
- **Python**: 3.10+.
- **VLM API Key**: Gemini or OpenRouter key in `.env`.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   Create a `.env` file:
   ```env
   GEMINI_API_KEY=your_key_here
   # or
   OPENROUTER_API_KEY=your_key_here
   AI_PROVIDER=gemini # or openrouter
   ```

## Running the Crawler

To start the crawler in Image-Only mode (default):

```bash
python run_ui.py
# or
python run_cli.py
```

## Verification

To verify that the crawler is not using XML/Source:
1. Run a crawl.
2. Check `crawler.log`.
3. Ensure no `getting page source` logs or XML parsing errors appear.
4. Verify text input works on login screens without crashing.

## Troubleshooting

- **Text Input Fails**: Ensure ADB keyboard is enabled or try `adb shell input text` manually to test.
- **Coordinates Off**: Check if the screenshot resolution matches the device resolution. The VLM might be hallucinating coordinates if the image is resized weirdly.
