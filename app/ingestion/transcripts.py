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
    from app.config import get_settings
    settings = get_settings()

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

        base_cmd = [
            yt_dlp_path,
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--skip-download",
            "--js-runtimes", "node",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--quiet",
            "-o", output_template,
        ]

        # Add cookies if configured or auto-detected
        cookies_added = False

        # 1. Check settings
        cookies_path_str = getattr(settings, "youtube_cookies_path", "")
        if cookies_path_str:
            cookies_path = Path(cookies_path_str)
            if cookies_path.exists():
                base_cmd.extend(["--cookies", str(cookies_path)])
                cookies_added = True
                print(f"Using YouTube cookies from settings path: {cookies_path}")

        # 2. Auto-detect cookies.txt or youtube_cookies.txt in root or data/
        if not cookies_added:
            for candidate in ["cookies.txt", "youtube_cookies.txt", "data/cookies.txt", "data/youtube_cookies.txt"]:
                p = Path(candidate)
                if p.exists():
                    base_cmd.extend(["--cookies", str(p)])
                    cookies_added = True
                    print(f"Auto-detected and using YouTube cookies from: {p}")
                    break

        # 3. Check browser cookies
        cookies_browser = getattr(settings, "youtube_cookies_browser", "")
        if not cookies_added and cookies_browser:
            base_cmd.extend(["--cookies-from-browser", cookies_browser])
            print(f"Using cookies from browser: {cookies_browser}")

        # Retry with different player clients.
        # 'ios' is currently the most robust client for bypassing bot checks without cookies.
        # 'android,web' is the original fallback.
        client_configs = [
            ["youtube:player-client=ios"],
            ["youtube:player-client=android,web"]
        ]

        success = False
        error_msgs = []

        for config in client_configs:
            cmd = base_cmd + [
                "--extractor-args", config[0],
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            try:
                # Run with 120s timeout
                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                vtt_files = list(Path(tmpdir).glob("*.vtt"))
                if vtt_files:
                    success = True
                    break
            except subprocess.CalledProcessError as e:
                err = e.stderr.decode(errors="replace")
                error_msgs.append(f"Config {config}: {err[:200]}")
            except subprocess.TimeoutExpired:
                error_msgs.append(f"Config {config}: Timed out")

        if not success:
            print(f"yt-dlp failed for {video_id}. Attempted configurations:")
            for msg in error_msgs:
                print(f"  - {msg}")
            
            # Print helpful instructions for user to resolve bot checks
            if any("confirm you're not a bot" in m or "Sign in" in m for m in error_msgs):
                print("\n[TIP] YouTube bot detection triggered! To resolve this, you can:")
                print("1. Export cookies from your browser (e.g. using the 'Get cookies.txt' extension).")
                print("2. Save the cookies as 'cookies.txt' in the project root directory.")
                print("3. Or set YOUTUBE_COOKIES_PATH in your .env file to your cookies file path.")
                print("4. Or set YOUTUBE_COOKIES_BROWSER=chrome (or firefox/edge/safari) in your .env to read cookies directly from your local browser.\n")
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