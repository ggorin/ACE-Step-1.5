# CLAUDE.md — ACE-Step 1.5

## Project Overview

ACE-Step is an open-source music generation model using a **Language Model + Diffusion Transformer (DiT)** architecture. It generates full songs from text captions and lyrics, supporting multiple genres, languages, and audio editing modes (text-to-music, continuation, repainting).

## Environment Setup

- **Python**: 3.11–3.12
- **Package manager**: `uv` (not pip)
- **Virtual environment**: `uv venv && source .venv/bin/activate`
- **Install**: `uv sync`
- **Config**: `.env` file for API keys and settings (never commit)

## Key Commands

```bash
# Install dependencies
uv sync

# Download model checkpoints
acestep-download

# Run Gradio UI
python cli.py --share

# Run API server
acestep-api --host 0.0.0.0 --port 8000

# Run all tests
uv run python -m unittest discover -s . -p "*_test.py"
uv run python -m unittest discover -s . -p "test_*.py"

# Run single test file
uv run python -m unittest acestep.training.test_lora_utils

# Train LoRA
python train.py --config <config.toml>
```

## Architecture Map

```
acestep/                    # Core package
  acestep_v15_pipeline.py   # Main generation pipeline (entry point)
  api_server.py             # FastAPI server entry point
  api/                      # HTTP API routes, jobs, server setup
  core/                     # Generation handler, models, inference
  training/                 # LoRA/LoKr training utilities
  ui/gradio/                # Gradio interface components
  model_downloader.py       # Checkpoint download tool
  gpu_config.py             # Hardware detection (CUDA/MPS/ROCm/XPU/CPU)
  constants.py              # Shared constants
openrouter/                 # OpenRouter-compatible API server
rvc_pipeline/               # Seed-VC voice conversion pipeline
  convert.py                # Demucs → Seed-VC → FFmpeg recombine
scripts/                    # Utility scripts (GPU check, calibration)
docs/                       # Documentation
cli.py                      # Gradio CLI launcher
train.py                    # Training CLI
```

## Hardware Support

ACE-Step supports CUDA, MPS (Apple Silicon), ROCm (AMD), Intel XPU, MLX, and CPU. Hardware detection is centralized in `acestep/gpu_config.py`. Do not alter non-target platform paths unless required.

## Testing

- Framework: `unittest` (not pytest)
- Test file naming: `*_test.py` alongside source files
- Mocking: `unittest.mock.MagicMock` and `unittest.mock.patch`
- Run tests before submitting changes

## Code Conventions

See `AGENTS.md` for full details. Key points:

- `from __future__ import annotations` in new modules
- Logging: `from loguru import logger` (not `print()`)
- Strings: double quotes `"`
- Indent: 4 spaces
- Module size: target ≤150 LOC, hard cap 200 LOC
- Imports: stdlib → third-party → local, alphabetical within groups
- Type hints on new/modified functions
- Docstrings on all modules, classes, and public functions

## RVC Voice Conversion Pipeline

Located in `rvc_pipeline/`. Converts ACE-Step output vocals to a target voice:

1. **Demucs**: separates vocals from instrumental
2. **Seed-VC**: converts vocals to target voice (MPS accelerated)
3. **FFmpeg**: recombines into final mix

```bash
python rvc_pipeline/convert.py <input.mp3> --reference rvc_pipeline/reference/biggie_reference.wav
```

Extra dependencies: `demucs`, `seed-vc`, `yt-dlp`, `ffmpeg` (system)

## Files to Never Commit

- `.env` — API keys, secrets
- `checkpoints/` — model weights (downloaded via `acestep-download`)
- `loras/` — LoRA/LoKr trained weights
- `rvc_pipeline/reference/` — voice reference audio files
- `rvc_pipeline/temp/` — intermediate processing files
- `*.safetensors`, `*.ckpt` — model weight files
- `gradio_outputs/` — generated audio output
