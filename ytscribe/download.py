"""yt-dlp wrapper. Returns a dict describing what was downloaded."""
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal, TypedDict

import yt_dlp


class DownloadResult(TypedDict):
    title: str
    video_id: str
    audio_path: Path           # always populated; whisper input
    media_path: Path           # opus (audio mode) or video file (video mode)
    thumbnail_path: Path       # always converted to PNG
    intermediates: list[Path]  # working files safe to delete after mux
    mode: Literal["audio", "video"]


_SAFE = re.compile(r"[^A-Za-z0-9._一-鿿぀-ヿ㐀-䶿 -]")


def _slug(title: str) -> str:
    """Filesystem-safe but readable filename stem."""
    cleaned = _SAFE.sub("", title).strip()
    return cleaned or "ytscribe-output"


def _convert_thumb_to_png(src: Path) -> Path:
    """Re-encode any thumbnail to PNG so downstream H.264 can use it."""
    if src.suffix.lower() == ".png":
        return src
    out = src.with_suffix(".png")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-frames:v", "1",
         str(out)],
        check=True,
    )
    return out


def _extract_audio(media: Path) -> Path:
    """For video mode: pull the audio track out as opus for whisper."""
    out = media.with_suffix(".audio.opus")
    # First try stream-copy (works if source already opus)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(media),
         "-vn", "-c:a", "copy", str(out)],
    )
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        # Fall back to re-encode
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(media),
             "-vn", "-c:a", "libopus", "-b:a", "96k", str(out)],
            check=True,
        )
    return out


def fetch(url: str, mode: Literal["audio", "video"] = "audio",
          out_dir: Path | None = None) -> DownloadResult:
    out_dir = (out_dir or Path.cwd()).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    common: dict = {
        "writethumbnail": True,
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "restrictfilenames": False,
        "windowsfilenames": False,
    }

    if mode == "audio":
        opts = {
            **common,
            "format": "bestaudio[ext=opus]/bestaudio/best",
        }
    else:
        opts = {
            **common,
            "format": "bv*+ba/best",
            "merge_output_format": "mkv",
        }

    print(f"[download] {url} (mode={mode})", file=sys.stderr)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        media_path = Path(ydl.prepare_filename(info))
        # post-merge filename can change extension (e.g. webm → mkv); resolve
        if mode == "video" and not media_path.exists():
            stem = media_path.with_suffix("")
            for ext in (".mkv", ".mp4", ".webm"):
                cand = stem.with_suffix(ext)
                if cand.exists():
                    media_path = cand
                    break

    title = info.get("title", media_path.stem)
    video_id = info.get("id", "")

    # find thumbnail (yt-dlp writes it next to the media)
    thumb_candidates = list(out_dir.glob(f"{glob_escape(media_path.stem)}.*"))
    thumb_files = [p for p in thumb_candidates
                   if p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}]
    if not thumb_files:
        raise RuntimeError(
            f"No thumbnail found for {media_path.stem!r} in {out_dir}")
    original_thumb = thumb_files[0]
    thumb = _convert_thumb_to_png(original_thumb)

    if mode == "audio":
        audio_path = media_path
    else:
        audio_path = _extract_audio(media_path)

    intermediates: list[Path] = [thumb]
    if original_thumb != thumb:
        intermediates.append(original_thumb)
    if mode == "audio":
        intermediates.append(media_path)  # also == audio_path
    else:
        intermediates.append(audio_path)  # extracted .audio.opus

    return DownloadResult(
        title=title,
        video_id=video_id,
        audio_path=audio_path,
        media_path=media_path,
        thumbnail_path=thumb,
        intermediates=intermediates,
        mode=mode,
    )


def glob_escape(s: str) -> str:
    """Escape glob metacharacters in a literal filename stem."""
    return s.translate(str.maketrans({"[": "[[]", "]": "[]]", "*": "[*]",
                                       "?": "[?]"}))
