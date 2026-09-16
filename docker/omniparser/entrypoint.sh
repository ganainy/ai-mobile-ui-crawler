#!/usr/bin/env bash
set -euo pipefail

WEIGHTS_DIR="${WEIGHTS_DIR:-/app/weights}"
ICON_DETECT_WEIGHTS="${WEIGHTS_DIR}/icon_detect/model.pt"
# The microsoft/OmniParser-v2.0 HF repo currently ships this as icon_caption/, not
# icon_caption_florence/ as older docs/omniparserserver.py's --caption_model_path
# default assume. Check and pass the real folder name.
ICON_CAPTION_WEIGHTS="${WEIGHTS_DIR}/icon_caption/config.json"

if [[ ! -f "$ICON_DETECT_WEIGHTS" || ! -f "$ICON_CAPTION_WEIGHTS" ]]; then
    echo "[entrypoint] Model weights missing under ${WEIGHTS_DIR}, downloading microsoft/OmniParser-v2.0 from HuggingFace..."
    hf download microsoft/OmniParser-v2.0 --local-dir "$WEIGHTS_DIR"

    # Defensive: some environments nest the download under weights/weights (a known
    # pitfall on Windows hosts per docs/readmes/local-omniparser-setup.md). Flatten
    # it if it happens here too.
    if [[ -d "${WEIGHTS_DIR}/weights" ]]; then
        echo "[entrypoint] Flattening nested ${WEIGHTS_DIR}/weights directory..."
        mv "${WEIGHTS_DIR}/weights/"* "$WEIGHTS_DIR/"
        rmdir "${WEIGHTS_DIR}/weights"
    fi
fi

cd /app/omnitool/omniparserserver

exec python -m omniparserserver \
    --host 0.0.0.0 \
    --port 8000 \
    --device cuda \
    --som_model_path ../../weights/icon_detect/model.pt \
    --caption_model_path ../../weights/icon_caption \
    "$@"
