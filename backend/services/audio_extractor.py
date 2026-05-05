import asyncio
import subprocess
from pathlib import Path


async def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """
    Extract audio from video using FFmpeg.
    Returns path to the extracted WAV file.
    """
    audio_path = output_dir / "audio.wav"

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",                  # No video
        "-acodec", "pcm_s16le", # PCM 16-bit
        "-ar", "16000",         # 16kHz sample rate (Whisper preferred)
        "-ac", "1",             # Mono channel
        "-y",                   # Overwrite output
        str(audio_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {stderr.decode()}")

    if not audio_path.exists():
        raise RuntimeError("Audio file was not created by FFmpeg")

    return audio_path
