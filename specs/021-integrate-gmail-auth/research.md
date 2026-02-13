# Research Findings: Integrate Gmail Auth

## Decisions
1. **Target Account Management**: Implement a `GmailAccountSwitcher` that:
   - Identifies the currently active account (by reading labels in the menu or profile ring content-desc).
   - If a mismatch is detected, taps the profile icon and selects the correct account from the list.
2. **Persistence**: The `ConfigManager` will be updated to store `target_gmail_account`. This will be loaded into `GmailAutomationConfig`.
3. **UI Integration**: Add a generic "Test Credentials" field for the Gmail account in the Desktop Application's settings panel.

## Rationale
- **Auto-Switching**: Essential for reliability on multi-account devices.
- **Global Settings**: Standardizes configuration for all crawl sessions.
- **Plain Text**: Increases usability (user can see which account is active).

## Technical Details
- **Profile Icon ID**: `com.google.android.gm:id/og_apd_ring_view` (Common in Google apps).
- **Account List Item**: `//android.widget.TextView[contains(@text, '{email}')]`
- **Active Account Detection**: Check `content-desc` of the profile icon or open the account picker and check for "Signed in as" labels.

## Alternatives Considered
- **ADB Only Account Switch**: Tricky and depends on internal Gmail intents/databases. UI automation is more portable across app versions.
- **Manual Switching**: Rejection: Does not meet the "automated" requirement of the feature spec.
