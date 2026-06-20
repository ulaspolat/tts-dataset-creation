# YouTube audio downloader

Local step of the [TTS dataset pipeline](../README.md): download YouTube video or playlist audio as **mono WAV** files (default **24 kHz**), for TTS dataset preparation.

```bash
cd youtube_audio_downloader
pip install -r requirements.txt
```

**Requirements:** Python 3.10+, [FFmpeg](https://ffmpeg.org/download.html) on your PATH.

Outputs go to `./data` by default (created in the current working directory). Files are named `{title}__{video_id}.wav`. Existing files are skipped. Playlist runs also write `download_log.txt` in the output folder.

**Only download content you have the right to use** (your own videos, licensed material, etc.).

## Single video

```bash
python download_single_audio.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Playlist

```bash
python download_playlist_audio.py "https://www.youtube.com/playlist?list=PLxxxxxxxx"
```

## Options (both scripts)

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir` | `./data` | Where WAV files are saved |
| `--sample-rate` | `24000` | Output sample rate (Hz) |
| `--channels` | `1` | Output channels (`1` = mono) |

Playlist only:

| Flag | Default | Description |
|------|---------|-------------|
| `--max-retries` | `3` | Retries per video |
| `--retry-delay` | `5` | Seconds between retries |
