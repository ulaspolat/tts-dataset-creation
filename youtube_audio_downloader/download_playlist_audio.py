#!/usr/bin/env python3
"""
Robust YouTube Playlist Audio Downloader
Downloads audio from all videos in a YouTube playlist as WAV files.
Designed for fault tolerance with large playlists (100+ videos).
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

import yt_dlp

from audio_utils import (
    DEFAULT_OUTPUT_DIR,
    build_audio_ydl_opts,
    cleanup_temp_files,
    convert_to_wav_ffmpeg,
    find_downloaded_file,
    video_url_from_info,
    wav_output_path,
)


def setup_logging(output_dir: Path) -> logging.Logger:
    """Configure logging with both file and console output."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "download_log.txt"

    logger = logging.getLogger("PlaylistDownloader")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def download_video_audio(
    video_info: Dict[str, Any],
    output_dir: Path,
    logger: logging.Logger,
    sample_rate: int,
    channels: int,
    max_retries: int,
    retry_delay: int,
) -> bool:
    """Download audio from a single video with retry logic."""
    video_url = video_url_from_info(video_info)
    if not video_url:
        logger.error("No URL for video entry; skipping")
        return False

    video_title = video_info.get("title") or f"video_{video_info.get('id', 'unknown')}"
    video_id = video_info.get("id", "unknown")
    final_output = wav_output_path(output_dir, video_title, video_id)

    if final_output.exists():
        logger.info(f"Already exists, skipping: {final_output.name}")
        return True

    logger.info(f"Downloading: {video_title}")
    logger.info(f"Video ID: {video_id}")
    logger.info(f"URL: {video_url}")

    temp_output = output_dir / f"temp_{video_id}"
    ydl_opts = build_audio_ydl_opts(temp_output, max_retries)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            downloaded_file = find_downloaded_file(temp_output)
            if not downloaded_file:
                raise FileNotFoundError(f"Downloaded file not found for: {video_title}")

            ok, err = convert_to_wav_ffmpeg(
                downloaded_file, final_output, sample_rate, channels
            )
            if ok:
                try:
                    downloaded_file.unlink()
                except OSError as e:
                    logger.warning(f"Could not delete temp file {downloaded_file}: {e}")
                logger.info(f"Successfully downloaded: {final_output.name}")
                return True

            if downloaded_file.exists():
                downloaded_file.unlink()
            raise RuntimeError(err or "WAV conversion failed")

        except Exception as e:
            logger.error(f"Attempt {attempt} failed: {e}")
            cleanup_temp_files(temp_output)

            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed after {max_retries} attempts: {video_title}")
                return False

    return False


def get_playlist_videos(playlist_url: str, logger: logging.Logger) -> list:
    """Extract video information from a playlist."""
    logger.info(f"Fetching playlist information from: {playlist_url}")

    ydl_opts = {
        "extract_flat": True,
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)

            if not playlist_info or "entries" not in playlist_info:
                logger.error("No videos found in playlist")
                return []

            videos = [entry for entry in playlist_info["entries"] if entry is not None]
            logger.info(f"Found {len(videos)} videos in playlist")
            return videos

    except Exception as e:
        logger.error(f"Error fetching playlist: {e}")
        return []


def download_playlist(
    playlist_url: str,
    output_dir: Path,
    logger: logging.Logger,
    sample_rate: int,
    channels: int,
    max_retries: int,
    retry_delay: int,
) -> int:
    """
    Download audio from all videos in a playlist.

    Returns:
        Number of failed downloads.
    """
    logger.info("=" * 80)
    logger.info("YouTube Playlist Audio Downloader")
    logger.info("=" * 80)
    logger.info(f"Output directory: {output_dir.resolve()}")
    logger.info(f"Format: WAV, {sample_rate}Hz, {channels} channel(s)")
    logger.info("=" * 80)

    output_dir.mkdir(parents=True, exist_ok=True)
    videos = get_playlist_videos(playlist_url, logger)

    if not videos:
        logger.error("No videos to download. Exiting.")
        return 1

    total_videos = len(videos)
    successful_downloads = 0
    failed_downloads = 0
    skipped_downloads = 0

    logger.info(f"Starting download of {total_videos} videos")
    logger.info("=" * 80)

    for idx, video_info in enumerate(videos, 1):
        logger.info(f"\n[{idx}/{total_videos}] Processing video {idx}")
        logger.info("-" * 80)

        try:
            video_id = video_info.get("id", "unknown")
            video_title = video_info.get("title") or f"video_{video_id}"
            final_output = wav_output_path(output_dir, video_title, video_id)

            if final_output.exists():
                logger.info(f"Already downloaded: {final_output.name}")
                skipped_downloads += 1
                continue

            if download_video_audio(
                video_info,
                output_dir,
                logger,
                sample_rate,
                channels,
                max_retries,
                retry_delay,
            ):
                successful_downloads += 1
            else:
                failed_downloads += 1

        except KeyboardInterrupt:
            logger.warning("\nDownload interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error processing video {idx}: {e}")
            failed_downloads += 1

    logger.info("\n" + "=" * 80)
    logger.info("Download Summary")
    logger.info("=" * 80)
    logger.info(f"Total videos in playlist: {total_videos}")
    logger.info(f"Successfully downloaded: {successful_downloads}")
    logger.info(f"Skipped (already exists): {skipped_downloads}")
    logger.info(f"Failed downloads: {failed_downloads}")
    logger.info(f"Output directory: {output_dir.resolve()}")
    logger.info("=" * 80)

    return failed_downloads


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download all audio from a YouTube playlist as WAV files."
    )
    parser.add_argument(
        "playlist_url",
        help="YouTube playlist URL (e.g. https://www.youtube.com/playlist?list=PLxxxx)",
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
        help="Download/conversion retries per video (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=5,
        help="Seconds to wait between retries (default: 5)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    playlist_url = args.playlist_url

    if "youtube.com/playlist" not in playlist_url and "list=" not in playlist_url:
        print("Invalid YouTube playlist URL", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    logger = setup_logging(output_dir)

    try:
        failed = download_playlist(
            playlist_url,
            output_dir,
            logger,
            args.sample_rate,
            args.channels,
            args.max_retries,
            args.retry_delay,
        )
        logger.info("\nDownload process completed!")
        sys.exit(1 if failed else 0)

    except KeyboardInterrupt:
        logger.warning("\n\nProcess interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
