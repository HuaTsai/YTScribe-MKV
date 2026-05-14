"""faster-whisper wrapper. GPU first, CPU fallback."""
import sys
from pathlib import Path
from typing import Iterable

from faster_whisper import WhisperModel

MAX_SEG_SEC = 8.0
SPLIT_GAP_SEC = 0.7


def _load_model(name: str) -> WhisperModel:
    try:
        m = WhisperModel(name, device="cuda", compute_type="float16")
        print(f"[transcribe] loaded {name} on CUDA/float16", file=sys.stderr)
        return m
    except Exception as e:
        print(f"[transcribe] CUDA unavailable ({e.__class__.__name__}: {e}); "
              f"falling back to CPU/int8", file=sys.stderr)
        return WhisperModel(name, device="cpu", compute_type="int8")


def _split_segment(seg) -> list[dict]:
    """Break long mega-segments at word-level gaps."""
    words = seg.words or []
    if not words or (seg.end - seg.start) <= MAX_SEG_SEC:
        return [{"start": seg.start, "end": seg.end, "text": seg.text.strip()}]

    out: list[dict] = []
    cur_words: list = []
    cur_start = words[0].start
    last_end = words[0].end
    for w in words:
        gap = w.start - last_end
        cur_len = w.end - cur_start
        if cur_words and (gap >= SPLIT_GAP_SEC or cur_len > MAX_SEG_SEC):
            text = "".join(x.word for x in cur_words).strip()
            if text:
                out.append({"start": cur_start, "end": last_end, "text": text})
            cur_words = []
            cur_start = w.start
        cur_words.append(w)
        last_end = w.end
    if cur_words:
        text = "".join(x.word for x in cur_words).strip()
        if text:
            out.append({"start": cur_start, "end": last_end, "text": text})
    return out


def run(audio_path: Path, model_name: str = "large-v3",
        language: str = "ja",
        initial_prompt: str = "ASMR、優しい囁き声と擬音語、相槌。"
        ) -> list[dict]:
    """Transcribe and return raw segment dicts (post word-split, pre-clean)."""
    model = _load_model(model_name)
    print(f"[transcribe] {audio_path.name}", file=sys.stderr)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=False,
        word_timestamps=True,
        condition_on_previous_text=False,
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.6,
        initial_prompt=initial_prompt,
    )
    print(f"[transcribe] detected language={info.language} "
          f"prob={info.language_probability:.2f} duration={info.duration:.1f}s",
          file=sys.stderr)

    out: list[dict] = []
    raw = 0
    for s in segments:
        raw += 1
        out.extend(_split_segment(s))
        if raw % 20 == 0:
            print(f"[transcribe] raw={raw} split={len(out)} t={s.end:.1f}s",
                  file=sys.stderr)
    print(f"[transcribe] done: raw={raw} split={len(out)}", file=sys.stderr)
    return out
