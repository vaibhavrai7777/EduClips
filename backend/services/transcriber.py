import os
import asyncio
from pathlib import Path
from typing import Optional

# We support both local Whisper and OpenAI API
USE_OPENAI_API = os.getenv("USE_OPENAI_API", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def transcribe_audio(audio_path: Path) -> dict:
    """
    Transcribe audio using Whisper.
    Returns dict with 'text' and 'segments' (with timestamps).
    """
    if USE_OPENAI_API and OPENAI_API_KEY:
        return await _transcribe_openai_api(audio_path)
    else:
        return await _transcribe_local_whisper(audio_path)


async def _transcribe_openai_api(audio_path: Path) -> dict:
    """Use OpenAI hosted Whisper API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    with open(audio_path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    for seg in response.segments:
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    return {
        "text": response.text,
        "segments": segments,
        "language": response.language,
    }


async def _transcribe_local_whisper(audio_path: Path) -> dict:
    """Use local Whisper model (fallback, requires whisper installed)."""
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "Local Whisper not installed and no OpenAI API key provided. "
            "Either set OPENAI_API_KEY or install openai-whisper: pip install openai-whisper"
        )

    # Run in thread pool to avoid blocking async loop
    loop = asyncio.get_event_loop()

    def _run_whisper():
        model = whisper.load_model("base")  # Use "small" or "medium" for better accuracy
        result = model.transcribe(
            str(audio_path),
            word_timestamps=False,
            verbose=False,
        )
        segments = []
        for seg in result["segments"]:
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            })
        return {
            "text": result["text"],
            "segments": segments,
            "language": result.get("language", "en"),
        }

    return await loop.run_in_executor(None, _run_whisper)
