#!/usr/bin/env python3
"""
Simple YouTube Single Video Audio Downloader
Downloads audio from a single YouTube video as a WAV file via FFmpeg.
"""

import argparse
import sys
from pathlib import Path

import yt_dlp

from audio_utils import (
    DEFAULT_OUTPUT_DIR,
    build_audio_ydl_opts,
    cleanup_temp_files,
    convert_to_wav_ffmpeg,
    find_downloaded_file,
    wav_output_path,
)


def download_video(
    video_url: str,
    output_dir: Path,
    sample_rate: int,
    channels: int,
    max_retries: int,
) -> bool:
    """Download audio from a YouTube video and convert to WAV."""
    print("=" * 80)
    print("YouTube Single Video Audio Downloader")
    print("=" * 80)
    print(f"Output directory: {output_dir.resolve()}")
    print(f"Format: WAV, {sample_rate}Hz, {channels} channel(s)")
    print("=" * 80)
    print()

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching video information...")
    ydl_info_opts = {"quiet": True, "no_warnings": True}

    try:
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get("title", "Unknown Title")
            video_id = info.get("id", "unknown")
            duration = info.get("duration") or 0

            print(f"Title: {video_title}")
            print(f"Video ID: {video_id}")
            print(
                f"Duration: {duration // 3600}h "
                f"{(duration % 3600) // 60}m {duration % 60}s"
            )
            print()

            final_output = wav_output_path(output_dir, video_title, video_id)
            temp_output = output_dir / f"temp_{video_id}"

            if final_output.exists():
                print(f"File already exists: {final_output.name}")
                return True

    except Exception as e:
        print(f"Error fetching video info: {e}")
        return False

    print("Downloading audio (this may take a while for long videos)...")
    print()

    ydl_opts = build_audio_ydl_opts(temp_output, max_retries)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        print()
        print("Download complete!")
        print()

        downloaded_file = find_downloaded_file(temp_output)
        if not downloaded_file:
            print("Error: Downloaded file not found")
            cleanup_temp_files(temp_output)
            return False

        size_gb = downloaded_file.stat().st_size / (1024**3)
        print(f"Downloaded file size: {size_gb:.2f} GB")
        print()
        print(f"Converting to WAV: {downloaded_file.name}")

        ok, err = convert_to_wav_ffmpeg(
            downloaded_file, final_output, sample_rate, channels
        )
        if ok:
            try:
                downloaded_file.unlink()
                print("Temporary file deleted")
            except OSError as e:
                print(f"Warning: Could not delete temp file: {e}")

            print()
            print("=" * 80)
            print("SUCCESS! Audio saved to:")
            print(f"  {final_output.resolve()}")
            print("=" * 80)
            return True

        print(f"Conversion to WAV failed: {err}")
        print(f"Temp file kept at: {downloaded_file}")
        return False

    except Exception as e:
        print(f"Error during download: {e}")
        cleanup_temp_files(temp_output)
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download audio from a YouTube video as a WAV file."
    )
    parser.add_argument(
        "video_url",
        help="YouTube video URL (e.g. https://www.youtube.com/watch?v=xxxx)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for WAV files (default: ./data)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=24000,
        help="Output sample rate in Hz (default: 24000)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1,
        help="Output channel count (default: 1 = mono)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="yt-dlp retries for download (default: 3)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    video_url = args.video_url

    if "youtube.com/watch" not in video_url and "youtu.be/" not in video_url:
        print("Invalid YouTube video URL", file=sys.stderr)
        sys.exit(1)

    try:
        success = download_video(
            video_url,
            Path(args.output_dir),
            args.sample_rate,
            args.channels,
            args.max_retries,
        )
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback

        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
