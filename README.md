# YTScribe-MKV

YouTube → faster-whisper → Claude translation → single MKV, in one command.

## Requirements

- Python 3.12 (managed by `uv`)
- `ffmpeg` / `ffprobe` on `PATH`
- `claude` CLI on `PATH` (logged in)
- One JS runtime on `PATH` — `deno`, `node`, or `bun`
  (YouTube needs JS to solve its download URL challenge; auto-detected)
- Optional: NVIDIA GPU for ~10–30× faster transcription
  (CUDA libs come bundled via the `nvidia-*-cu12` wheels; auto-loaded)

### Installing a JS runtime

```bash
# Deno (recommended — single binary, sandboxed):
curl -fsSL https://deno.land/install.sh | sh

# or Node:
sudo apt install nodejs           # Ubuntu/Debian
```

Without one, you'll see `Requested format is not available` from yt-dlp.

## Install

```bash
uv sync
```

## Usage

### Public video

```bash
uv run main.py "https://www.youtube.com/watch?v=..."
```

### Channel-membership-only video

You need to be logged in to YouTube and be a paying member of the channel.

```bash
# pull cookies from your browser session (easiest)
uv run main.py --cookies-from-browser chrome "<URL>"

# specify a profile if you use multiple
uv run main.py --cookies-from-browser "firefox:default" "<URL>"
uv run main.py --cookies-from-browser "brave:Profile 1" "<URL>"

# or pass a Netscape-format cookies.txt
uv run main.py --cookies cookies.txt "<URL>"
```

Caveats:

- **Close the browser** when using `--cookies-from-browser` for
  Chrome/Edge/Brave — they lock the cookies DB while running. Firefox is
  unaffected.
- On Linux + Chrome/Brave, cookie decryption needs `secretstorage` (already
  a dependency) plus a running GNOME Keyring or KWallet.
- Cookies expire; if you get `Sign in to confirm` or `members-only content`
  errors, re-pull them.

### All options

```
url                                YouTube video URL
--mode {audio,video}               audio-only (default) or full video
--model MODEL                      faster-whisper model (default: large-v3)
--out-dir DIR                      output directory (default: cwd)
--cookies-from-browser BROWSER[:PROFILE]
                                   extract cookies from a local browser
--cookies FILE                     Netscape cookies.txt file
```

## Output

A single file is left in the output directory:

- `<title>.mkv` — H.264 still-image (or original video) + opus audio +
  Japanese SRT + Traditional Chinese SRT + cover art

All intermediate files (downloaded audio, thumbnails, raw SRTs) are
removed after a successful mux.

## Pipeline

1. `yt-dlp` downloads media + thumbnail (with JS-runtime-assisted URL solving)
2. `faster-whisper large-v3` transcribes Japanese (GPU first, CPU fallback)
3. Post-process to drop Whisper's `ご視聴ありがとう` hallucinations and
   merge word-internal splits
4. `claude` CLI translates the SRT into Traditional Chinese (Taiwan)
5. `ffmpeg` muxes audio + cover + both subtitle tracks into one MKV
6. Cleanup removes every working file except the final MKV
