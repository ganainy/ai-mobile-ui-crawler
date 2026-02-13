# Quickstart: UI/UX Features

This guide explains the new UI organization and features introduced in the `020-ui-ux-improvements` update.

## 1. Async Operations

Long-running tasks no longer freeze the interface.

- **Device Refresh**: Click "Refresh" in the Device Selector. A spinner will appear, and you can still switch tabs.
- **App Listing**: Listing apps is now non-blocking.
- **Model Loading**: Fetching global AI models happens in the background.

## 2. New Settings Layout

Settings are now organized into tabs for easier navigation:

- **General**: Crawl limits (Steps/Duration), Limit Mode, Screen Config (Top Bar).
- **AI Settings**: Provider selection, API Keys, System Prompt.
- **Integrations**: Service integrations like PCAPdroid (Traffic), MobSF, Video Recording.
- **Credentials**: Test account credentials and Mailosaur configuration.

## 3. Persistent Preferences

- **Step-by-Step Mode**: The checkbox state is now saved. If you enable it, close the app, and reopen it, it will remain enabled.

## 4. Run History

- The Run History panel at the bottom now defaults to a larger height, showing multiple past runs at a glance.
- You can resize the panel using the splitter handle.

## 5. Troubleshooting

- **UI Freezes**: If a freeze occurs, check the logs (Right Panel > Logs) to see if an error occurred in a background thread.
- **Logs**: Use `File > Open Session Folder` (new) to view session artifacts and output data.
