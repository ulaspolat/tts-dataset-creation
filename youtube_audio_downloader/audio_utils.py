"""Shared helpers for YouTube audio download scripts."""

import re
import subprocess
from pathlib import Path
from typing import Optional

DEFAULT_OUTPUT_DIR = Path("./data")

TEMP_EXTENSIONS = (".m4a", ".mp3", ".opus", ".webm", ".ogg", ".part")


def sanitize_filename(filename: str) -> str:
    """Make a string safe for use in filenames on Windows and Linux."""
    filename = filename.strip()
    filename = re.sub(r'["\'“”‘’«»‹›]', "", filename)
    invalid_chars = r'[<>:"/\\|?*|]'
    filename = re.sub(invalid_chars, "_", filename)
    filename = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", filename)
    filename = re.sub(r"[_\s]+", "_", filename)
    filename = filename.strip(" ._")
    filename = filename.strip("_")
    if len(filename) > 200:
        filename = filename[:200]
    return filename if filename else "untitled"


def wav_output_path(output_dir: Path, title: str, video_id: str) -> Path:
    """Build the final WAV path: {sanitized_title}__{video_id}.wav"""
    safe_title = sanitize_filename(title)
    return output_dir / f"{safe_title}__{video_id}.wav"


def video_url_from_info(video_info: dict) -> Optional[str]:
    """Resolve a watch URL from yt-dlp metadata (including flat playlist entries)."""
    url = video_info.get("webpage_url") or video_info.get("url")
    if url:
        return url
    video_id = video_info.get("id")
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return None


def find_downloaded_file(temp_output: Path) -> Optional[Path]:
    """Locate the intermediate audio file yt-dlp wrote for a temp prefix."""
    for ext in TEMP_EXTENSIONS:
        if ext == ".part":
            continue
        candidate = Path(str(temp_output) + ext)
        if candidate.exists():
            return candidate
    return None


def cleanup_temp_files(temp_output: Path) -> None:
    """Remove leftover temp/intermediate files for a download attempt."""
    for ext in TEMP_EXTENSIONS:
        temp_file = Path(str(temp_output) + ext)
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


def convert_to_wav_ffmpeg(
    input_file: Path,
    output_file: Path,
    sample_rate: int,
    channels: int,
) -> tuple[bool, Optional[str]]:
    """
    Convert audio to WAV using FFmpeg (handles large files).

    Returns:
        (success, error_message)
    """
    cmd = [
        "ffmpeg",
        "-i",
        str(input_file),
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        "-y",
        str(output_file),
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return False, (
            "FFmpeg not found. Install FFmpeg and add it to PATH: "
            "https://ffmpeg.org/download.html"
        )
    except OSError as e:
        return False, str(e)

    if result.returncode == 0:
        return True, None
    return False, result.stderr.strip() or "FFmpeg conversion failed"


def build_audio_ydl_opts(temp_output: Path, max_retries: int) -> dict:
    """yt-dlp options for best-audio download with FFmpeg extract."""
    return {
        "format": "bestaudio/best",
        "outtmpl": str(temp_output),
        "quiet": False,
        "no_warnings": False,
        "retries": max_retries,
        "fragment_retries": max_retries,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ],
    }
