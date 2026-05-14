"""YTScribe-MKV — uv run main.py <YT-URL> [--mode video|audio]"""
# Set LD_LIBRARY_PATH for bundled CUDA libs and re-exec BEFORE importing
# anything that touches faster-whisper / ctranslate2.
from ytscribe.cuda_bootstrap import ensure_cuda_libs
ensure_cuda_libs()

import argparse
import shutil
import sys
from pathlib import Path

from ytscribe import clean, download, mux, srt, transcribe, translate


def cleanup_workspace(info: dict, ja_srt: Path, zh_srt: Path,
                       keep: Path) -> None:
    """Remove all working files so only the final MKV remains."""
    keep_resolved = keep.resolve()
    targets: list[Path] = [ja_srt, zh_srt, *info.get("intermediates", [])]
    seen: set[Path] = set()
    for p in targets:
        try:
            rp = Path(p).resolve()
        except OSError:
            continue
        if rp == keep_resolved or rp in seen or not rp.exists():
            continue
        seen.add(rp)
        try:
            rp.unlink()
        except OSError as e:
            print(f"[cleanup] could not remove {rp.name}: {e}",
                  file=sys.stderr)


def preflight() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        sys.exit("error: ffmpeg/ffprobe not found on PATH")
    translate.assert_claude_available()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ytscribe",
        description="YouTube → faster-whisper → Claude → MKV pipeline.",
    )
    p.add_argument("url", help="YouTube video URL")
    p.add_argument("--mode", choices=["video", "audio"], default="audio",
                   help="download full video or audio-only (default: audio)")
    p.add_argument("--model", default="large-v3",
                   help="faster-whisper model name (default: large-v3)")
    p.add_argument("--out-dir", type=Path, default=None,
                   help="output directory (default: current working dir)")
    p.add_argument("--cookies-from-browser", metavar="BROWSER[:PROFILE]",
                   default=None,
                   help="extract cookies from a local browser "
                        "(e.g. 'chrome', 'firefox:default'); required for "
                        "channel-membership-only videos")
    p.add_argument("--cookies", type=Path, default=None, metavar="FILE",
                   help="path to a Netscape-format cookies.txt file "
                        "(alternative to --cookies-from-browser)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    preflight()

    info = download.fetch(args.url, mode=args.mode, out_dir=args.out_dir,
                           cookies_from_browser=args.cookies_from_browser,
                           cookies_file=args.cookies)

    base_dir = (args.out_dir or Path.cwd()).resolve()
    stem = Path(info["media_path"]).stem
    ja_srt = base_dir / f"{stem}.ja.srt"
    zh_srt = base_dir / f"{stem}.zh.srt"
    out_mkv = base_dir / f"{stem}.mkv"

    raw_segs = transcribe.run(Path(info["audio_path"]),
                              model_name=args.model)
    cleaned = clean.process(raw_segs)
    if not cleaned:
        sys.exit("error: no transcribable speech found")

    srt.write(cleaned, ja_srt)
    print(f"[srt] wrote {ja_srt.name} ({len(cleaned)} entries)",
          file=sys.stderr)

    translate.via_claude(ja_srt, zh_srt)

    mux.build(info=info, ja_srt=ja_srt, zh_srt=zh_srt,
              output=out_mkv, mode=args.mode)

    cleanup_workspace(info, ja_srt=ja_srt, zh_srt=zh_srt, keep=out_mkv)
    print(f"\n✓ {out_mkv}")


if __name__ == "__main__":
    main()
