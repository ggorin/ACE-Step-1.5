# ACE-Step CLI Generation & Voice Conversion Workflow

## Prerequisites

```bash
cd ~/Projects/ace_step
source .venv/bin/activate
```

Ensure checkpoints are downloaded: `acestep-download`

## Step 1: Start the API Server

```bash
acestep-api --host 127.0.0.1 --port 8001
```

Options:
- `--init-llm` — force LM init (needed for `thinking=True` / sample mode)
- `--lm-model-path acestep-5Hz-lm-0.6B` — choose LM size (0.6B, 1.7B, 4B)
- `--no-init` — skip model loading at startup (lazy-load on first request)
- `--api-key <key>` — set auth key (or set `ACESTEP_API_KEY` in `.env`)

If `ACESTEP_API_KEY` is not set in `.env`, auth is disabled (no token needed).

## Step 2: Submit a Generation Job

```bash
curl -s -X POST http://127.0.0.1:8001/release_task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "East coast hip hop, boom bap, male rapper, aggressive flow, 90s rap, 95 BPM, key of C minor",
    "lyrics": "[verse]\nFirst line of verse\nSecond line of verse\n[chorus]\nChorus line here",
    "audio_duration": 75,
    "batch_size": 1,
    "task_type": "text2music",
    "inference_steps": 8,
    "guidance_scale": 7.0
  }' | python3 -m json.tool
```

### Key Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | str | `""` | Caption describing genre, mood, instruments, BPM, key |
| `lyrics` | str | `""` | Lyrics with section tags: `[verse]`, `[chorus]`, `[bridge]`, `[outro]` |
| `audio_duration` | float | auto | Duration in seconds (max depends on GPU tier) |
| `batch_size` | int | 1 | Number of variations to generate |
| `task_type` | str | `"text2music"` | `text2music`, `continuation`, `repainting` |
| `inference_steps` | int | 8 | Diffusion steps (more = higher quality, slower) |
| `guidance_scale` | float | 7.0 | CFG scale (higher = more prompt adherence) |
| `seed` | int | -1 | Random seed (-1 = random) |
| `thinking` | bool | false | Use 5Hz LM for audio code generation (requires LM loaded) |
| `sample_mode` | bool | false | Auto-generate caption/lyrics via LM |
| `audio_format` | str | `"mp3"` | Output format: `mp3`, `flac`, `wav`, `wav32`, `opus`, `aac` |
| `vocal_language` | str | `"en"` | Vocal language code |
| `bpm` | int | null | Explicit BPM (or include in prompt) |
| `key_scale` | str | `""` | Musical key (e.g., `"C minor"`) |
| `reference_audio_path` | str | null | Path to reference audio for style matching |
| `src_audio_path` | str | null | Source audio for continuation/repainting |
| `repainting_start` | float | 0.0 | Repaint region start (0.0-1.0) |
| `repainting_end` | float | null | Repaint region end (0.0-1.0) |

### Auth

If `ACESTEP_API_KEY` is set, include one of:
- Body field: `"ai_token": "your-key"`
- Header: `-H "Authorization: Bearer your-key"`

## Step 3: Poll for Result

The `/release_task` response returns a `task_id`. Poll with:

```bash
curl -s -X POST http://127.0.0.1:8001/query_result \
  -H "Content-Type: application/json" \
  -d '{
    "task_id_list": "[\"<TASK_ID>\"]"
  }' | python3 -m json.tool
```

Status codes in response:
- `1` = queued/pending
- `2` = running
- `0` = completed (audio paths in response)
- Negative = error

Output files land in `gradio_outputs/`.

## Step 4: Voice Conversion (Biggie Pipeline)

Convert generated song vocals to target voice:

```bash
python rvc_pipeline/convert.py gradio_outputs/<output>.mp3 \
  --reference rvc_pipeline/reference/biggie_juicy_official_acapella.wav \
  --output gradio_outputs/<output>_biggie.mp3
```

### Pipeline Steps
1. **Demucs** — separates vocals + instrumental
2. **Seed-VC** — converts vocals to target voice (MPS accelerated, fp16=False)
3. **FFmpeg** — recombines with volume balancing (vocals 1.2x, instrumental 0.9x)

### Available References (best to good)

| Reference | Quality | Notes |
|-----------|---------|-------|
| `biggie_juicy_official_acapella.wav` | Best | Studio acapella, cleanest tone |
| `biggie_juicy_reference.wav` | Great | Original manually prepared clip (default) |
| `biggie_big_poppa_acapella.wav` | Great | Studio acapella |
| `biggie_hypnotize_acapella.wav` | Good | Studio acapella, smoother delivery |
| `biggie_notorious_thugs_acapella.wav` | Good | Studio acapella, fast flow |
| `biggie_warning_studio.wav` | Good | Raw studio recording, 37s |
| `biggie_sway_freestyle_1997.wav` | Fair | Demucs-isolated, some artifacts |
| `biggie_brooklyn_freestyle_17.wav` | Fair | Street recording, lo-fi |

## Full One-Liner Example

Generate + convert in sequence (after API server is running):

```bash
# Generate
TASK_ID=$(curl -s -X POST http://127.0.0.1:8001/release_task \
  -H "Content-Type: application/json" \
  -d '{"prompt":"90s boom bap hip hop, male rapper, gritty, 95 BPM, C minor","lyrics":"[verse]\nIt was all a dream\nI used to read Word Up magazine","audio_duration":75}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('task_id',''))")

echo "Task ID: $TASK_ID"

# Poll until done (check every 10s)
while true; do
  RESULT=$(curl -s -X POST http://127.0.0.1:8001/query_result \
    -H "Content-Type: application/json" \
    -d "{\"task_id_list\": \"[\\\"$TASK_ID\\\"]\"}")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',[{}])[0].get('status',1))" 2>/dev/null)
  echo "Status: $STATUS"
  [ "$STATUS" = "0" ] && break
  sleep 10
done

echo "$RESULT" | python3 -m json.tool

# Voice convert the output
python rvc_pipeline/convert.py gradio_outputs/<output>.mp3 \
  --reference rvc_pipeline/reference/biggie_juicy_official_acapella.wav
```

## Alternative: Gradio UI

For interactive use with preview/playback:

```bash
acestep --share  # public link
acestep          # local only at http://127.0.0.1:7860
```
