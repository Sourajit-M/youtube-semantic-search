import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import webvtt


def fetch_transcript(video_id: str) -> Optional[str]:
    """
    Downloads and parses the transcript for a YouTube video.
    Returns clean transcript text, or None if unavailable.
    """
    import sys

    # Resolve yt-dlp executable path dynamically from the current virtual env
    yt_dlp_path = "yt-dlp"
    venv_bin = Path(sys.executable).parent
    for candidate in ["yt-dlp.exe", "yt-dlp"]:
        candidate_path = venv_bin / candidate
        if candidate_path.exists():
            yt_dlp_path = str(candidate_path)
            break

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = str(Path(tmpdir) / "%(id)s.%(ext)s")

        cmd = [
            yt_dlp_path,
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--skip-download",
            "--js-runtimes", "node",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--extractor-args", "youtube:player-client=android,web",
            "--quiet",
            "-o", output_template,
            f"https://www.youtube.com/watch?v={video_id}",
        ]

        try:
            # Increase timeout to 120s for longer videos
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            print(f"yt-dlp failed for {video_id}: {e.stderr.decode()[:200]}")
            return None
        except subprocess.TimeoutExpired:
            print(f"yt-dlp timed out for {video_id}")
            return None

        vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if not vtt_files:
            print(f"No transcript found for {video_id}")
            return None

        return _parse_vtt(vtt_files[0])


def _parse_vtt(vtt_path: Path) -> Optional[str]:
    try:
        seen: set[str] = set()
        lines: list[str] = []

        # Decode raw bytes with errors='replace' so no byte ever raises.
        # Pass encoding='utf-8' to webvtt.read() to avoid Windows falling
        # back to cp1252 (which chokes on 0x92 smart-quotes, etc.).
        raw = vtt_path.read_bytes().decode("utf-8", errors="replace")
        clean_path = vtt_path.with_suffix(".clean.vtt")
        clean_path.write_text(raw, encoding="utf-8")

        for caption in webvtt.read(str(clean_path), encoding="utf-8"):
            # Parse start time cue MM:SS.fff or HH:MM:SS.fff to integer seconds
            start_sec = 0
            try:
                parts = caption.start.split(':')
                if len(parts) == 3:
                    h, m, s = parts
                    start_sec = int(h) * 3600 + int(m) * 60 + int(float(s))
                elif len(parts) == 2:
                    m, s = parts
                    start_sec = int(m) * 60 + int(float(s))
            except Exception:
                pass

            for line in caption.text.strip().splitlines():
                line = line.strip()
                line = re.sub(r'<[^>]+>', '', line)
                if line and line not in seen:
                    seen.add(line)
                    # Embed time marker in the text
                    lines.append(f"[t={start_sec}] {line}")

        return ' '.join(lines) if lines else None

    except Exception as e:
        print(f"VTT parse error: {e}")
        return None