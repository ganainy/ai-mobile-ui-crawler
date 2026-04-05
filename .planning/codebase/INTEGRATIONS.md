# External Integrations

**Analysis Date:** 2026-04-05

## APIs & External Services

**AI/LLM Providers:**
- Google Gemini (via google-genai)
  - Models: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0, gemini-3-pro-preview
  - Auth: GEMINI_API_KEY or GOOGLE_API_KEY environment variable
  - Features: Vision capabilities for multimodal AI interaction
- OpenAI (via OpenRouter API)
  - Models: GPT-4, GPT-4o, Claude 3 series
  - Auth: OPENAI_API_KEY environment variable
  - Features: Via OpenRouter proxy
- Anthropic Claude (via OpenRouter API)
  - Models: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
  - Auth: ANTHROPIC_API_KEY environment variable
  - Features: Via OpenRouter proxy
- Ollama (Local)
  - Models: Llama, Mistral, custom models
  - Auth: None (local server)
  - Base URL: http://localhost:11434 (configurable)
- OpenRouter API
  - Models: Multiple provider models via unified API
  - Auth: OPENROUTER_API_KEY environment variable

**Mobile Device Platforms:**
- Android via ADB (Android Debug Bridge)
  - Connection: Direct USB/ADB
  - Tools: `adb.exe` from Android SDK
- Appium Server
  - Connection: HTTP/JSON Wire Protocol
  - Client: appium-python-client
  - Port: 4723 (configurable)

## Data Storage

**Databases:**
- SQLite (crawler.db)
  - Connection: Local file storage
  - Client: Built-in sqlite3 with custom DatabaseManager
  - Location: App data directory
  - Schema: Runs, screens, steps, AI interactions, logs

**File Storage:**
- Local filesystem - Screenshots, reports, logs, session data
- Session folders: Organized by run ID and timestamp

**Caching:**
- In-memory caching for provider model registry
- SQLite for persistent data storage

## Authentication & Identity

**Auth Provider:**
- Custom authentication via API keys
- Secret management via encrypted credential store
- Multiple AI provider support with different key formats

## Monitoring & Observability

**Error Tracking:**
- Custom logging to console and files
- JSONL format for structured logs (DroidRun traces)
- Error tracking via logging service

**Logs:**
- Python logging module
- Multiple sinks: console, file, database
- Structured JSON logging for AI interactions
- DroidRun-specific JSONL traces

## CI/CD & Deployment

**Hosting:**
- Local execution (script-based)
- No external deployment detected

**CI Pipeline:**
- pytest for automated testing
- ruff for code quality
- Pre-commit hooks for quality enforcement

## Environment Configuration

**Required env vars:**
- GEMINI_API_KEY or GOOGLE_API_KEY (for Gemini)
- OPENAI_API_KEY (for OpenAI via OpenRouter)
- ANTHROPIC_API_KEY (for Anthropic via OpenRouter)
- OPENROUTER_API_KEY (for OpenRouter API)
- Optional: ADB_PATH for custom ADB location

**Secrets location:**
- CredentialStore encrypted storage
- Environment variables fallback
- Configuration files (not recommended for production)

## Webhooks & Callbacks

**Incoming:**
- ADB device callbacks for device detection
- Appium server events

**Outgoing:**
- REST API calls to AI providers
- DroidRun agent API calls (internal)
- HTTP requests for model fetching

## Additional Integrations

**Email Services:**
- Mailosaur API (via mailosaur Python SDK)
  - Purpose: OTP and magic link retrieval
  - Auth: API key in configuration
  - Features: Email/SMS message search and parsing

**Security Scanning:**
- MobSF (Mobile Security Framework)
  - Purpose: Static application security testing
  - Connection: Local server integration
  - Output: Security reports

**Network Analysis:**
- Packet capture via tcpdump/PCAP
  - Purpose: Network traffic analysis
  - Integration: PCAP file parsing and correlation

---

*Integration audit: 2026-04-05*