import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import webvtt


def fetch_transcript(video_id: str) -> Optional[str]:
    """
    Downloads and parses the transcript for a YouTube video.
    Attempts to fetch via youtube_transcript_api first (highly resistant to bot blocks).
    Falls back to yt-dlp if unavailable.
    """
    import sys
    import os
    import requests
    import http.cookiejar
    from app.config import get_settings
    settings = get_settings()

    # 1. Resolve and load cookies if configured or auto-detected
    cookies_path = None
    cookies_added = False
    temp_cookies_file = None

    # Check if cookies content is passed as an environment secret (e.g. on Hugging Face)
    cookies_content = os.environ.get("YOUTUBE_COOKIES_CONTENT", "")
    if cookies_content.strip():
        try:
            # Ensure the Netscape header is present at the start of the file
            header = "# Netscape HTTP Cookie File\n"
            content_to_write = cookies_content.strip()
            if not content_to_write.startswith("# Netscape"):
                content_to_write = header + content_to_write
            # Add a trailing newline to avoid EOF errors
            content_to_write += "\n"

            # Create a temporary file to hold the cookies
            fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="hf_cookies_")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content_to_write)
            cookies_path = Path(temp_path)
            temp_cookies_file = cookies_path
            cookies_added = True
            print("Loaded YouTube cookies dynamically from YOUTUBE_COOKIES_CONTENT environment secret.")
        except Exception as e:
            print(f"Failed to write YOUTUBE_COOKIES_CONTENT to temp file: {e}")

    # Check settings next
    if not cookies_added:
        cookies_path_str = getattr(settings, "youtube_cookies_path", "")
        if cookies_path_str:
            p = Path(cookies_path_str)
            if p.exists():
                cookies_path = p
                cookies_added = True
                print(f"Using YouTube cookies from settings path: {cookies_path}")

    # Auto-detect local files
    if not cookies_added:
        for candidate in ["cookies.txt", "youtube_cookies.txt", "data/cookies.txt", "data/youtube_cookies.txt"]:
            p = Path(candidate)
            if p.exists():
                cookies_path = p
                cookies_added = True
                print(f"Auto-detected and using YouTube cookies from: {p}")
                break

    try:
        # Attempt 1a: Try anonymous fetch using youtube_transcript_api + curl-cffi first
        # This is extremely successful for public videos on Hugging Face as it has browser-grade
        # TLS/headers but completely avoids Google's session hijack locks that trigger on datacenter IPs!
        try:
            from curl_cffi.requests import Session as CurlSession
            print(f"Attempting anonymous fetch for {video_id} using Chrome-impersonated curl-cffi Session...")
            anon_session = CurlSession(impersonate="chrome")
            
            from youtube_transcript_api import YouTubeTranscriptApi
            api_instance = YouTubeTranscriptApi(http_client=anon_session)
            transcript_list = api_instance.fetch(video_id, languages=['en'])
            
            seen: set[str] = set()
            lines: list[str] = []
            for entry in transcript_list:
                start_sec = int(entry.start)
                text = entry.text.strip()
                # Remove HTML tags if any
                text = re.sub(r'<[^>]+>', '', text)
                for line in text.splitlines():
                    line = line.strip()
                    if line and line not in seen:
                        seen.add(line)
                        lines.append(f"[t={start_sec}] {line}")
            
            if lines:
                print(f"Successfully fetched transcript anonymously.")
                return ' '.join(lines)
        except Exception as anon_err:
            print(f"Anonymous youtube-transcript-api fetch failed for {video_id}: {anon_err}")

        # Attempt 1b: Try authenticated fetch with cookies if anonymous fetch failed
        if cookies_path:
            try:
                from curl_cffi.requests import Session as CurlSession
                print(f"Attempting authenticated fetch for {video_id} with cookies...")
                auth_session = CurlSession(impersonate="chrome")
                cj = http.cookiejar.MozillaCookieJar()
                cj.load(str(cookies_path), ignore_discard=True, ignore_expires=True)
                auth_session.cookies = cj
                
                from youtube_transcript_api import YouTubeTranscriptApi
                api_instance = YouTubeTranscriptApi(http_client=auth_session)
                transcript_list = api_instance.fetch(video_id, languages=['en'])
                
                seen: set[str] = set()
                lines: list[str] = []
                for entry in transcript_list:
                    start_sec = int(entry.start)
                    text = entry.text.strip()
                    # Remove HTML tags if any
                    text = re.sub(r'<[^>]+>', '', text)
                    for line in text.splitlines():
                        line = line.strip()
                        if line and line not in seen:
                            seen.add(line)
                            lines.append(f"[t={start_sec}] {line}")
                
                if lines:
                    print(f"Successfully fetched transcript using authenticated cookies.")
                    return ' '.join(lines)
            except Exception as auth_err:
                print(f"Authenticated youtube-transcript-api fetch failed for {video_id}: {auth_err}")
        else:
            # Standard requests fallback in case curl-cffi is not used
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                print(f"Attempting standard requests anonymous fetch for {video_id}...")
                transcript_list = YouTubeTranscriptApi().fetch(video_id, languages=['en'])
                
                seen: set[str] = set()
                lines: list[str] = []
                for entry in transcript_list:
                    start_sec = int(entry.start)
                    text = entry.text.strip()
                    # Remove HTML tags if any
                    text = re.sub(r'<[^>]+>', '', text)
                    for line in text.splitlines():
                        line = line.strip()
                        if line and line not in seen:
                            seen.add(line)
                            lines.append(f"[t={start_sec}] {line}")
                
                if lines:
                    print(f"Successfully fetched transcript using standard requests anonymous fetch.")
                    return ' '.join(lines)
            except Exception as std_err:
                print(f"Standard requests anonymous fetch failed for {video_id}: {std_err}")

        # Attempt 2: Fall back to yt-dlp
        print(f"Falling back to yt-dlp for {video_id}...")

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
                "--quiet",
                "-o", output_template,
            ]

            # Apply cookies if we have them
            if cookies_path:
                base_cmd.extend(["--cookies", str(cookies_path)])
            else:
                # Check browser cookies fallback if no file
                cookies_browser = getattr(settings, "youtube_cookies_browser", "")
                if cookies_browser:
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
    finally:
        # Cleanup temporary cookies file if created
        if temp_cookies_file and temp_cookies_file.exists():
            try:
                temp_cookies_file.unlink()
                print("Cleaned up temporary YouTube cookies file.")
            except Exception as cleanup_err:
                print(f"Error cleaning up temporary cookies file: {cleanup_err}")


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