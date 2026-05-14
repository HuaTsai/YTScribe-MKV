"""ffmpeg muxing — final MKV with audio (and optionally video) + 2 subs."""
import subprocess
import sys
from pathlib import Path
from typing import Literal


def build(*, info: dict, ja_srt: Path, zh_srt: Path, output: Path,
          mode: Literal["audio", "video"]) -> None:
    output = Path(output)
    if output.exists():
        output.unlink()
    title = info.get("title", output.stem)
    if mode == "audio":
        _build_audio_mode(
            cover=Path(info["thumbnail_path"]),
            audio=Path(info["audio_path"]),
            ja_srt=Path(ja_srt),
            zh_srt=Path(zh_srt),
            output=output,
            title=title,
        )
    else:
        _build_video_mode(
            video=Path(info["media_path"]),
            cover=Path(info["thumbnail_path"]),
            ja_srt=Path(ja_srt),
            zh_srt=Path(zh_srt),
            output=output,
            title=title,
        )


def _build_audio_mode(*, cover: Path, audio: Path, ja_srt: Path,
                       zh_srt: Path, output: Path, title: str) -> None:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-loop", "1", "-framerate", "1", "-i", str(cover),
        "-i", str(audio),
        "-i", str(ja_srt),
        "-i", str(zh_srt),
        "-map", "0:v", "-map", "1:a", "-map", "2:s", "-map", "3:s",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast",
        "-crf", "28", "-pix_fmt", "yuv420p", "-r", "1",
        "-c:a", "copy",
        "-c:s", "srt",
        "-shortest",
        "-metadata:s:a:0", "language=jpn",
        "-metadata:s:s:0", "language=jpn",
        "-metadata:s:s:0", "title=Japanese",
        "-metadata:s:s:1", "language=chi",
        "-metadata:s:s:1", "title=Chinese (Traditional)",
        "-metadata", f"title={title}",
        str(output),
    ]
    print(f"[mux] (audio) → {output.name}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def _build_video_mode(*, video: Path, cover: Path, ja_srt: Path,
                       zh_srt: Path, output: Path, title: str) -> None:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video),
        "-i", str(ja_srt),
        "-i", str(zh_srt),
        "-attach", str(cover),
        "-metadata:s:t:0", "mimetype=image/png",
        "-metadata:s:t:0", "filename=cover.png",
        "-map", "0:v:0", "-c:v", "copy",
        "-map", "0:a:0", "-c:a", "copy",
        "-map", "1:s", "-map", "2:s",
        "-c:s", "srt",
        "-metadata:s:a:0", "language=jpn",
        "-metadata:s:s:0", "language=jpn",
        "-metadata:s:s:0", "title=Japanese",
        "-metadata:s:s:1", "language=chi",
        "-metadata:s:s:1", "title=Chinese (Traditional)",
        "-metadata", f"title={title}",
        str(output),
    ]
    print(f"[mux] (video) → {output.name}", file=sys.stderr)
    subprocess.run(cmd, check=True)
