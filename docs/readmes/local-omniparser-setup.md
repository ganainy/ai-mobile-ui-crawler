# Local OmniParser Setup Guide

This guide describes how to set up a local, high-performance **Microsoft OmniParser v2.0** server on your machine to work seamlessly with `mobile-crawler`. Running OmniParser locally eliminates external API dependencies (such as Replicate), reduces cost, and improves performance.

## Current mobile-crawler Integration Status

`mobile-crawler` stores OmniParser settings in the GUI Settings panel and passes them into the internalized `crawler_agent` runtime. The default parser mode is `boost`, which uses Android accessibility data first and falls back to OmniParser when accessibility metadata is sparse or unavailable.

Use the local backend when you have a local OmniParser server running at the configured URL. Use the Replicate backend when you prefer the cloud API and have a Replicate API key configured.

---

## 🐳 Recommended: Docker

The easiest and most reproducible way to run OmniParser locally is the Docker image in
[`docker/omniparser/`](../../docker/omniparser/README.md). It handles cloning OmniParser, applying
the patches below, and downloading model weights, with GPU (CUDA) support built in.

```powershell
cd docker/omniparser
docker compose up --build
```

See [`docker/omniparser/README.md`](../../docker/omniparser/README.md) for prerequisites (Docker
Desktop + WSL2 GPU passthrough), configuration (`HF_TOKEN` for faster weight downloads), and the
reasoning behind its non-obvious choices (base image, dependency overrides, etc.). It's been
verified working end-to-end against an RTX 5070 (Blackwell).

Once running, it listens on `http://localhost:8001` (host port 8000 is reserved for MobSF) — the same default `omniparser_local_url`
`mobile-crawler` already expects, so no client config changes are needed beyond switching the
**OmniParser Backend** setting to `local` (see [Connecting to mobile-crawler UI](#-connecting-to-mobile-crawler-ui) below).

The rest of this guide describes the manual (non-Docker) setup, useful if you're not on Windows
with Docker Desktop, or want a native Python environment instead.

---

## 🛠️ Manual Setup (alternative to Docker)

### 1. Clone OmniParser Repository & Setup Environment
Clone the official OmniParser repository into a directory of your choice and initialize a Python 3.10-3.12 virtual environment:

```powershell
# Clone the repository
git clone https://github.com/microsoft/OmniParser.git E:\OmniParser
cd E:\OmniParser

# Initialize Python Virtual Environment
python -m venv .venv
.venv\Scripts\activate

# Install Core dependencies
pip install -r requirements.txt
```

### 2. Install PyTorch
Depending on whether you have a GPU or are running on CPU, install the appropriate version of PyTorch:

* **For CPU Mode (No GPU):**
  ```powershell
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  ```

* **For CUDA Mode (NVIDIA GPU):**
  ```powershell
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  ```
  Note: Blackwell (RTX 50-series, `sm_120`) GPUs need PyTorch ≥2.7 built against CUDA ≥12.8
  instead — the `cu121` wheel above won't recognize those cards. See the Docker image's base
  image choice for a known-working combo.

---

## 📦 Model Weights Setup

OmniParser relies on two pre-trained models: YOLOv8 (icon detection) and Florence-2 (icon description/captioning).

1. Create a `weights` directory inside the repository:
   ```powershell
   mkdir weights
   ```

2. Download the official model weights from HuggingFace. You can use the `huggingface-cli` tool:
   ```powershell
   pip install huggingface_hub
   huggingface-cli download microsoft/OmniParser-v2.0 --local-dir weights
   ```

3. **CRITICAL: Resolve the Double Weights Path Pitfall**
   Under Windows, the HuggingFace CLI might download weights nested into a duplicate directory structure (e.g. `weights/weights/icon_caption`). You **MUST** move these folders to the root of the `weights` directory so the server can resolve them:
   ```powershell
   # Move florence caption folder to main weights directory
   Move-Item -Path "E:\OmniParser\weights\weights\icon_caption" -Destination "E:\OmniParser\weights\" -Force
   
   # Remove duplicate nested folder
   Remove-Item -Path "E:\OmniParser\weights\weights" -Recurse -Force
   ```
   Your final `E:\OmniParser\weights\` directory **MUST** look like this:
   ```text
   E:\OmniParser\weights\
   ├── icon_detect/
   │   ├── model.pt
   │   └── ...
   └── icon_caption/
       ├── config.json
       └── ...
   ```
   Note: upstream's HF repo currently ships this folder as `icon_caption/`. Older versions of this
   guide (and `omniparserserver.py`'s own `--caption_model_path` default) call it
   `icon_caption_florence/` — if you're on an older weights snapshot with that name, either rename
   it to `icon_caption` or pass `--caption_model_path` pointing at whichever name you actually have.

---

## 🩹 Essential Fixes & Patches

When running the server, you will encounter two legacy issues/deprecation crashes on newer Python packages. Follow these exact fixes to resolve them:

### Fix 1: PaddleOCR Deprecation / Arg-Parsing Crash
In `util/utils.py` (around line 23), PaddleOCR initialization contains deprecated parameters that cause it to crash with `unexpected keyword argument` or `ccache` warnings when defaulted:
1. Open [util/utils.py](file:///E:/OmniParser/util/utils.py).
2. Look for the `paddle_ocr = PaddleOCR(...)` initializer — it spans several lines, ending at the
   closing `)`.
3. Replace the **entire multi-line call** with the minimal constructor to let it use modern defaults:
   ```python
   paddle_ocr = PaddleOCR(lang='en', use_angle_cls=False)
   ```
   (Replacing only the first line and leaving the original arguments below it will cause an
   `IndentationError` — make sure the whole block, opening to closing parenthesis, is replaced.)

### Fix 2: Florence-2 Causal LM Crash on newer `transformers`
Newer `transformers` releases changed generation-config handling in a way that breaks Florence-2's
custom modeling code. On CPU this surfaces as `AttributeError: '_supports_sdpa' is not defined`;
on GPU it surfaces as `AttributeError: 'Florence2LanguageConfig' object has no attribute
'forced_bos_token_id'` — same root cause, pin the same fix regardless of device:
```powershell
pip install "transformers==4.45.2"
```

---

## 🚀 Running the Local Server

Once weights are arranged and the patches are applied, activate your virtual environment and start the FastAPI server:

```powershell
# Navigate to the server directory
cd E:\OmniParser\omnitool\omniparserserver

# Start the server (default runs on port 8000)
python -m omniparserserver
```

* Ensure it prints `Omniparser initialized!!!` and `INFO: Uvicorn running on http://127.0.0.1:8000` without any exceptions.

---

## 📱 Connecting to mobile-crawler UI

The `mobile-crawler` Settings panel is fully integrated with this local setup (Docker or manual):
1. Open the `mobile-crawler` Desktop application.
2. Open the **Settings Panel** (under Crawler/Exploration settings).
3. Under the **UI Parser** configuration:
   - Change the **OmniParser Backend** to `local`.
   - Set the **Local OmniParser URL** to `http://localhost:8001` (default).
   - Keep **Local Parse Timeout** at `120` seconds for CPU inference, or lower it if your GPU setup consistently returns faster.
4. Save and launch your crawl loop! The crawler will now bypass the cloud APIs and use your lightning-fast local CPU/GPU inference instead.

> `mobile-crawler` starts this Docker stack automatically at GUI launch when the UI parser mode uses OmniParser and the backend is `local`.
