# OmniParser server (Docker)

Containerizes Microsoft's [OmniParser](https://github.com/microsoft/OmniParser) server so it
can run locally without a manual Python/CUDA environment setup. See
[`docs/readmes/local-omniparser-setup.md`](../../docs/readmes/local-omniparser-setup.md) for the
non-Docker setup this replaces, and for background on the two upstream patches.

## Prerequisites

- Docker Desktop with the **WSL2 backend**, and the NVIDIA driver's WSL/CUDA support installed
  on the Windows host. Native Windows containers cannot do GPU passthrough.
- Verify GPU access before building:
  ```powershell
  docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
  ```

## Build & run

```powershell
cd docker/omniparser
docker compose up --build
```

First run downloads ~GB of model weights from HuggingFace into `docker/omniparser/weights/`
(bind-mounted, so this only happens once — later rebuilds reuse it). The server listens on
`localhost:8000`, which is `mobile-crawler`'s existing default `omniparser_local_url` — no client
config changes needed, just switch the **OmniParser Backend** setting to `local`.

## Non-obvious choices

- **Base image is `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime`, not the `cu121` wheel from
  the manual setup doc.** Blackwell GPUs (RTX 50-series, `sm_120`) need PyTorch ≥2.7 built
  against CUDA ≥12.8; anything older won't recognize the GPU at all. If you're on an older
  (pre-Blackwell) card, the `cu121` combo from the manual doc will also work fine.
- **OmniParser is pinned to a specific commit** (`OMNIPARSER_COMMIT` build arg in the
  `Dockerfile`), not tracking `master`, so builds are reproducible. Bump it deliberately.
- **`torch`/`torchvision` are stripped from OmniParser's `requirements.txt`** before install, so
  they don't clobber the base image's matched CUDA 12.8 build.
- **`uiautomation` is also stripped.** It's Windows-only (used by OmniTool's separate GUI-agent
  demo, not by `omniparserserver.py`) and fails to install on the Linux base image.
- **`transformers` is pinned to `4.45.2`, same as the manual doc**, though for a broader reason
  than the doc states: it's not just a CPU-only `_supports_sdpa` crash. A newer `transformers`
  changed generation-config handling in a way that also breaks GPU inference for Florence-2's
  custom modeling code (`AttributeError: 'Florence2LanguageConfig' object has no attribute
  'forced_bos_token_id'`), confirmed against this image's stack.
- **`--device cuda` is passed explicitly** — the upstream server defaults to CPU inference even
  when a GPU is available.
- **`--caption_model_path` points at `weights/icon_caption`, not `weights/icon_caption_florence`
  as `omniparserserver.py`'s own default and the manual doc assume.** The current
  `microsoft/OmniParser-v2.0` HF repo ships that folder as `icon_caption/` — the doc's layout has
  drifted from upstream. `entrypoint.sh` checks and passes the real folder name.

## Verified working

Built and run end-to-end against an RTX 5070 (Blackwell) on 2026-09-16: `docker compose up
--build` serves `GET /probe/` → `200 {"message":"Omniparser API ready"}` on `localhost:8000`.
