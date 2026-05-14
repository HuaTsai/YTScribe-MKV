"""SubRip writer."""
from pathlib import Path


def format_time(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def write(segments: list[dict], path: Path) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n"
                    f"{format_time(s['start'])} --> {format_time(s['end'])}\n"
                    f"{s['text']}\n\n")
