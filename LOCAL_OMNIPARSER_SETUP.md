# Local OmniParser Setup Guide

This guide describes how to set up a local, high-performance **Microsoft OmniParser v2.0** server on your machine to work seamlessly with `mobile-crawler` (DroidRun). Running OmniParser locally eliminates external API dependencies (such as Replicate), reduces cost, and improves performance.

---

## 🛠️ Step-by-Step Installation

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
   Under Windows, the HuggingFace CLI might download weights nested into a duplicate directory structure (e.g. `weights/weights/icon_caption_florence`). You **MUST** move these folders to the root of the `weights` directory so the server can resolve them:
   ```powershell
   # Move florence caption folder to main weights directory
   Move-Item -Path "E:\OmniParser\weights\weights\icon_caption_florence" -Destination "E:\OmniParser\weights\" -Force
   
   # Remove duplicate nested folder
   Remove-Item -Path "E:\OmniParser\weights\weights" -Recurse -Force
   ```
   Your final `E:\OmniParser\weights\` directory **MUST** look like this:
   ```text
   E:\OmniParser\weights\
   ├── icon_detect/
   │   ├── model.pt
   │   └── ...
   └── icon_caption_florence/
       ├── config.json
       └── ...
   ```

---

## 🩹 Essential Fixes & Patches

When running the server, you will encounter two legacy issues/deprecation crashes on newer Python packages. Follow these exact fixes to resolve them:

### Fix 1: PaddleOCR Deprecation / Arg-Parsing Crash
In `util/utils.py` (around line 23), PaddleOCR initialization contains deprecated parameters that cause it to crash with `unexpected keyword argument` or `ccache` warnings when defaulted:
1. Open [util/utils.py](file:///E:/OmniParser/util/utils.py).
2. Look for the `paddle_ocr = PaddleOCR(...)` initializer.
3. Replace it with the minimal constructor to let it use modern defaults:
   ```python
   paddle_ocr = PaddleOCR(lang='en', use_angle_cls=False)
   ```

### Fix 2: Florence-2 Causal LM SDPA Attribute Crash
When running the model on CPU, you will hit an `AttributeError: '_supports_sdpa' is not defined` inside PyTorch's/Transformers' attention layer. 
To resolve this, downgrade the `transformers` library in the virtual environment to `4.45.2`:
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

The `mobile-crawler` Settings panel is fully integrated with this local setup:
1. Open the `mobile-crawler` Desktop application.
2. Open the **Settings Panel** (under Crawler/Exploration settings).
3. Under the **UI Parser** configuration:
   - Change the **OmniParser Backend** to `local`.
   - Set the **Local OmniParser URL** to `http://localhost:8000` (default).
4. Save and launch your crawl loop! The crawler will now bypass the cloud APIs and use your lightning-fast local CPU/GPU inference instead.
