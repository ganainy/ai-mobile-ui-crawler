---
author: claude
---
# Design grill: is a ready-made AI tool the answer for login/signup?

User asked whether a ready-made AI automation tool exists for login/signup, since it's the step they struggle with most. Grilled to a concrete answer instead of a tool survey.

## What the grill settled

- The live pain is **CAPTCHA** — OTP typing (digit-drop bug) and social/Google sign-in are already stabilized by recent sessions.
- CAPTCHA policy: fall to Human Fallback, full stop. No third-party CAPTCHA-solving service (2captcha etc.) — automating a solve against a bot-deterrent sits in murkier ToS territory than automating one's own test account, and was explicitly rejected.
- Any tooling must stay local/self-hosted (credentials + OTP already touch real accounts and SMS/email inboxes) and operate on native Android UI (ADB/accessibility tree), not a browser — ruling out most "AI login automation" products (browser-use, Skyvern, etc.), which drive DOM/CDP.
- This echoes the 2026-09-20 UI-detection decision (`docs/sessions/2026-09-20-ui-detection-options.md`): no third parser, no bolted-on local model. Same conclusion here: no ready-made external tool needed.

## What the grill found (the real gap)

- Zero CAPTCHA detection anywhere in `src/`.
- `RequestKind.MANUAL_STEP` (`src/mobile_crawler/domain/human_fallback.py:19`) is defined but dead code — never triggered.
- The only caller of `human_fallback.request` is `authentication.py:232`, hardcoded to `RequestKind.CODE`, fired by Python when an automatic OTP lookup fails.
- The agent (Manager/Executor LLM) has no tool to request a human handoff on its own judgment. Confirmed behavior: it flails at a stuck screen until step/attempt limits end the run, with no clean signal of why.

## Outcome

Filed as [issue #32](https://github.com/ganainy/ai-mobile-ui-crawler/issues/32) (an agent-callable manual-handoff tool wired to `MANUAL_STEP`, plus a CAPTCHA-recognition prompt rule, designed alongside the target-recovery guard). Scoped as research this session — the fix itself needs its own grill/spec pass. No code changed, no `CONTEXT.md`/ADR change (nothing new to name, nothing hard-to-reverse decided yet).
