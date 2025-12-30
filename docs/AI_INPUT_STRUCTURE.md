# AI Model Input Structure

## Overview
When **Image Context**, **OCR**, and **XML** are all enabled, the AI model receives a **multimodal input** consisting of:

1. **Text Prompt** (containing XML as JSON + OCR + metadata)
2. **Image** (preprocessed screenshot as PIL Image)

---

## Input Flow Architecture

```
┌─────────────────────┐
│  Screenshot Bytes   │
│  (from Appium)      │
└──────────┬──────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
    ┌──────────────┐            ┌─────────────────┐
    │ Image Prep   │            │  OCR Engine     │
    │ (resize,     │            │  (PaddleOCR)    │
    │  sharpen,    │            │                 │
    │  format)     │            └────────┬────────┘
    └──────┬───────┘                     │
           │                             │
           │                    ┌────────▼─────────┐
           │                    │ OCR Results      │
           │                    │ [{text, bounds,  │
           │                    │   confidence}]   │
           │                    └────────┬─────────┘
           │                             │
           │         ┌───────────────────┘
           │         │
           ▼         ▼
    ┌─────────────────────────────────┐
    │   LangChain Wrapper             │
    │   (Combines Text + Image)       │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │    Model Adapter                 │
    │    (Gemini/OpenRouter/Ollama)    │
    │    - Encodes image to base64     │
    │    - Formats multimodal request  │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │    AI Model API                  │
    │    (e.g., Gemini 1.5 Pro)        │
    └──────────────────────────────────┘
```

---

## Component 1: Text Prompt Structure

The text prompt is built by `PromptBuilder.format_prompt()` and contains:

### A. Static Part (Instructions)
```
=== CONTEXT (Static - Instructions) ===
<System prompt with:>
- Available actions (tap, scroll, type, etc.)
- JSON output schema
- Exploration journal rules
- Test credentials format
```

### B. Dynamic Part (Current State)
```
=== CURRENT STATE ===

**Screen Visit Context**: Visited 2 times.

**Last Action Outcome**:
Successfully tapped on "Login" button → Screen changed

**UI Elements (JSON Structure)**:
```json
{
  "elements": [
    {
      "id": 0,
      "type": "EditText",
      "resource_id": "com.example.app:id/email_input",
      "text": "",
      "content_desc": "Email address",
      "clickable": true,
      "bounds": [100, 300, 900, 400],
      "children": []
    },
    {
      "id": 1,
      "type": "EditText",
      "resource_id": "com.example.app:id/password_input",
      "text": "",
      "content_desc": "Password",
      "clickable": true,
      "password": true,
      "bounds": [100, 450, 900, 550],
      "children": []
    },
    {
      "id": 2,
      "type": "Button",
      "resource_id": "com.example.app:id/login_button",
      "text": "Sign In",
      "clickable": true,
      "bounds": [100, 600, 900, 700],
      "children": []
    }
  ]
}
```

**Visual Elements (OCR)**:
• ocr_0 = "Welcome Back!" [120, 150, 880, 220]
• ocr_1 = "Email" [115, 270, 200, 295]
• ocr_2 = "Password" [115, 420, 230, 445]
• ocr_3 = "Sign In" [400, 620, 600, 680]
• ocr_4 = "Forgot Password?" [350, 750, 650, 790]

=== EXPLORATION JOURNAL ===
Step 1: Launched app → Main screen (login required)
Step 2: Tapped "Get Started" → Login screen
Step 3: <current step>

**Actions Tried on This Screen (#42)**:
- tap on "Sign Up" link → Screen #43
- scroll down → Ineffective/Failed

**AUTHENTICATION STRATEGY**: 🔑 LOGIN (credentials exist for this app)
- Email: test@example.com
- Password: Test123!
- Name: Test User
→ When you see a login/signup choice, CHOOSE LOGIN and use these credentials.

**TASK**: Choose the next best action to maximize coverage. Respond in JSON.
```

---

## Component 2: Image Data

When `ENABLE_IMAGE_CONTEXT = True` and the model supports vision:

### Image Preprocessing Pipeline
Located in `AgentAssistant._prepare_image_part()`:

```python
# 1. Decode screenshot bytes to PIL Image
img = Image.open(io.BytesIO(screenshot_bytes))

# 2. Resize (preserve aspect ratio, no upscaling)
if img.width > IMAGE_MAX_WIDTH (e.g., 1024):
    scale = max_width / img.width
    new_height = int(img.height * scale)
    img = img.resize((max_width, new_height), LANCZOS)

# 3. Convert to RGB (for JPEG compatibility)
if img.mode in ('RGBA', 'LA', 'P'):
    background = Image.new('RGB', img.size, (255, 255, 255))
    background.paste(img, mask=alpha_channel)
    img = background

# 4. Apply mild sharpening (preserve text clarity)
img = img.filter(UnsharpMask(
    radius=2.0,
    percent=150,
    threshold=3
))

# 5. Return PIL Image (adapter encodes to base64 JPEG/PNG)
return img
```

### Image Attachment
The prepared image is passed to the model adapter:

```python
# In LangChainWrapper._llm_call()
response_text, metadata = self.model_adapter.generate_response(
    prompt=prompt_text,        # The full text prompt above
    image=prepared_image,      # PIL Image object
    image_format='JPEG',       # or 'PNG'
    image_quality=85           # 1-100
)
```

### Model Adapter Encoding
Each provider adapter (Gemini, OpenRouter, Ollama) handles encoding:

**Gemini Provider:**
```python
# Encodes PIL Image to inline base64 data
import base64
import io

buffer = io.BytesIO()
image.save(buffer, format='JPEG', quality=85, optimize=True)
image_bytes = buffer.getvalue()
image_b64 = base64.b64encode(image_bytes).decode('utf-8')

# Sends to API as:
{
    "contents": [{
        "parts": [
            {"text": prompt_text},
            {"inline_data": {
                "mime_type": "image/jpeg",
                "data": image_b64
            }}
        ]
    }]
}
```

**OpenRouter/Ollama:**
```python
# Similar encoding but using OpenAI-style message format
{
    "model": "model-name",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{image_b64}"
            }}
        ]
    }]
}
```

---

## Complete Example: What the AI Receives

### Multimodal Request Structure

When all three are enabled, the AI model receives:

**1. Text Content:**
```
=== CONTEXT (Static - Instructions) ===
[Full system prompt with JSON schema, available actions, etc.]

=== CURRENT STATE ===
**UI Elements (JSON Structure)**: 
{structured XML converted to JSON with element IDs, types, bounds, etc.}

**Visual Elements (OCR)**:
• ocr_0 = "Create Account" [200, 450, 800, 520]
• ocr_1 = "Already have an account? Sign in" [250, 900, 750, 950]
[All detected text with bounding boxes]

=== EXPLORATION JOURNAL ===
[AI's own maintained journal of exploration]

**TASK**: Choose the next best action...
```

**2. Image Content:**
```
[Base64-encoded JPEG image, ~50-200KB after compression]
- Resized to max 1024px width
- RGB format
- Sharpened for text clarity
- Optimized JPEG quality (85%)
```

### AI Model Processing

The vision-language model (e.g., Gemini 1.5 Pro) processes:
- **Text**: Understands instructions, XML structure, OCR annotations
- **Image**: Visual understanding of layout, colors, icons, actual appearance
- **Cross-modal**: Can verify OCR text against image, understand context that XML might miss

### Why All Three?

| Context Type | Strengths | Weaknesses |
|-------------|-----------|------------|
| **XML/JSON** | Precise element IDs, hierarchy, clickability | Misses visual text, images, custom views |
| **OCR** | Detects visible text (even in images/canvas) | No hierarchy, may miss non-text elements |
| **Image** | Complete visual context, layout understanding | Cannot tap precisely without XML bounds |

**Together**: The AI can:
1. See the screen layout (Image)
2. Read all visible text (OCR)
3. Know exact element locations and IDs for interaction (XML)
4. Make informed decisions using all three perspectives

---

## Configuration Flags

```python
# In config/app_config.py or UI settings

# Controls image attachment to model
ENABLE_IMAGE_CONTEXT = True  # Image + Text prompt

# Context source - HYBRID always includes XML + OCR
CONTEXT_SOURCE = [ContextSource.HYBRID]  # Always enabled

# Image preprocessing settings
IMAGE_MAX_WIDTH = 1024        # Resize target
IMAGE_QUALITY = 85            # JPEG quality (1-100)
IMAGE_FORMAT = 'JPEG'         # or 'PNG'
IMAGE_SHARPEN_RADIUS = 2.0
IMAGE_SHARPEN_PERCENT = 150
IMAGE_SHARPEN_THRESHOLD = 3
```

---

## Secure Screen Handling

When `FLAG_SECURE` is detected (app prevents screenshots):

```python
# In agent_assistant.py
if screenshot_bytes == PLACEHOLDER_1x1_BLACK_PNG:
    is_secure_screen = True
    screenshot_bytes = None  # Disable image context
    
    # Add warning to XML
    xml_context["_WARNING"] = "SECURE VIEW DETECTED. RELY ON XML."
```

**Result**: AI receives only text prompt (XML + OCR) without image.

---

## Log Output Example

When a decision is made, you can see in `crawler.log`:

```
📸 Image context is ENABLED (screenshot_bytes: 156789 bytes)
📸 Image prepared for AI: 1024x1820
📸 Image context: Including prepared image in AI request (size: (1024, 1820))
AI thinking... 0.5s   
AI thinking... 5.5s   
AI response received in 6.34s (with image)   

[2025-12-30 21:00:00] AI INPUT (dynamic context):
**UI Elements (JSON Structure)**:
{...}

**Visual Elements (OCR)**:
• ocr_0 = "Login" [400, 600, 600, 650]
...

[2025-12-30 21:00:06] AI OUTPUT (6.34s):
{
  "exploration_journal": "...",
  "actions": [{
    "action": "type",
    "target_identifier": "com.app:id/email",
    "input_text": "test@example.com",
    "reasoning": "Filling email field based on XML element and OCR confirmation"
  }]
}
```

---

## Summary

When **Image + OCR + XML** are all enabled:

✅ **Text Prompt** = Static instructions + Dynamic state (JSON XML + OCR annotations + journal)  
✅ **Image Attachment** = Preprocessed screenshot (resized, sharpened, JPEG-encoded)  
✅ **Multimodal Processing** = AI sees both structured data and visual context  
✅ **Result** = More accurate decisions, especially for visual-heavy apps  

The combination provides **redundancy** (OCR + XML for text) and **completeness** (Image for visual layout).
