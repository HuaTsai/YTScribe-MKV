# YTScribe-MKV

YouTube → faster-whisper → Claude translation → MKV in one command.

## Requirements

- Python 3.12 (managed by `uv`)
- `ffmpeg` / `ffprobe` on `PATH`
- `claude` CLI on `PATH` (logged in)
- Optional: NVIDIA GPU for ~10–30× faster transcription
  (CUDA libs come bundled via the `nvidia-*-cu12` wheels; auto-detected)

## Install

```bash
uv sync
```

## Usage

```bash
# audio-only mode (default): downloads opus, makes a still-image MKV
uv run main.py <YT-URL>

# full-video mode
uv run main.py <YT-URL> --mode video
```

Output (in current working directory):

- `<title>.opus` (audio mode) or `<title>.<ext>` (video mode)
- `<title>.ja.srt` — Japanese transcript
- `<title>.zh.srt` — Traditional Chinese translation
- `<title>.mkv` — final container (audio + 2 subs + cover)

## Pipeline

1. `yt-dlp` downloads media + thumbnail
2. `faster-whisper large-v3` transcribes Japanese (GPU first, CPU fallback)
3. Post-process to drop hallucinations and merge word-internal splits
4. `claude` CLI translates the SRT into Traditional Chinese
5. `ffmpeg` muxes everything into a mobile-VLC-friendly MKV
