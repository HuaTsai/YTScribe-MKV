"""Translate a Japanese SRT to Traditional Chinese via the local Claude CLI."""
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


def assert_claude_available() -> None:
    if shutil.which("claude") is None:
        sys.exit(
            "error: `claude` CLI not found on PATH.\n"
            "Install Claude Code first (https://claude.com/claude-code) "
            "and ensure `claude --version` works.")


def via_claude(ja_srt: Path, zh_srt: Path) -> None:
    """Pipe a translation prompt to `claude -p`. Claude writes the .zh.srt
    itself via its Write tool."""
    ja_srt = Path(ja_srt).resolve()
    zh_srt = Path(zh_srt).resolve()

    prompt = textwrap.dedent(f"""
        Read the Japanese SRT subtitle file at:
            {ja_srt}

        Translate every subtitle's text into natural Traditional Chinese
        (zh-Hant, Taiwan-style wording). Strict requirements:
        - keep the index numbers exactly as-is
        - keep the timestamps exactly as-is (do NOT shift them)
        - one translated entry per source entry — never merge or split
        - output a valid SubRip (.srt) file

        Context: this is whispered/ASMR conversational content. Keep tone
        soft and gentle. Render onomatopoeia naturally
        (e.g. はぁー → 啊～, よしよし → 乖乖, ぎゅー → 抱緊緊).
        If the original Japanese is clearly a Whisper misrecognition,
        translate the most plausible intended meaning.

        Use the Write tool to save the translated SRT to:
            {zh_srt}

        Do not print the translation to chat — write it to the file only.
        After writing, reply with just the word "done".
    """).strip()

    print(f"[translate] invoking claude → {zh_srt.name}", file=sys.stderr)
    r = subprocess.run(
        ["claude", "-p", prompt,
         "--allowed-tools", "Read,Write"],
    )
    if r.returncode != 0:
        sys.exit(f"error: claude CLI exited with code {r.returncode}")
    if not zh_srt.exists():
        sys.exit(f"error: claude did not produce expected file {zh_srt}")
    print(f"[translate] wrote {zh_srt.name}", file=sys.stderr)
