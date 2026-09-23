# syntax=docker/dockerfile:1
#
# Containerizes Microsoft's OmniParser server (github.com/microsoft/OmniParser),
# which is NOT part of this repo — it's cloned at build time and pinned to a commit.
# See README.md in this directory for why these choices were made.

FROM pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime

# Pin to a known-good commit; bump deliberately, not via floating master.
ARG OMNIPARSER_COMMIT=354021201345a96178360b28733573e27269f2de

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/microsoft/OmniParser.git . \
    && git checkout ${OMNIPARSER_COMMIT}

# Fix 1 (unconditional, from docs/architecture/readmes/local-omniparser-setup.md): PaddleOCR's
# constructor here passes deprecated kwargs that crash on modern paddleocr releases.
RUN sed -i \
    "/^paddle_ocr = PaddleOCR(/,/)/c\\paddle_ocr = PaddleOCR(lang='en', use_angle_cls=False)" \
    util/utils.py

# requirements.txt pins neither torch nor torchvision, and would otherwise clobber
# the base image's Blackwell-compatible (sm_120, CUDA 12.8) build. It also lists
# `uiautomation`, a Windows-only package used by OmniTool's separate GUI-agent demo,
# not by omniparserserver.py — it fails to install on Linux, so it's dropped too.
# transformers is also dropped and pinned to 4.45.2 explicitly (Fix 2): newer
# transformers changed generation-config handling in a way that breaks Florence-2's
# custom modeling code (AttributeError: 'Florence2LanguageConfig' object has no
# attribute 'forced_bos_token_id') — this hits on GPU too, not just the CPU crash
# the manual setup doc describes.
# fastapi/uvicorn are imported directly by omniparserserver.py but aren't listed
# in requirements.txt (only pulled in transitively via gradio), so add them explicitly.
RUN grep -viE '^(torch|torchvision|uiautomation|transformers)([=<>~ ]|$)' requirements.txt \
        > requirements.filtered.txt \
    && pip install --no-cache-dir --break-system-packages \
        -r requirements.filtered.txt fastapi uvicorn "transformers==4.45.2"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV WEIGHTS_DIR=/app/weights
VOLUME ["/app/weights"]

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
