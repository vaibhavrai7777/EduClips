import os
import json
import asyncio
from typing import List, Dict

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

CLIP_MIN_SECONDS = int(os.getenv("CLIP_MIN_SECONDS", "20"))
CLIP_MAX_SECONDS = int(os.getenv("CLIP_MAX_SECONDS", "60"))
NUM_CLIPS = int(os.getenv("NUM_CLIPS", "5"))


async def select_clips(transcript: dict) -> List[Dict]:
    """
    Use GPT-4o to analyze transcript and select the best 3-5 educational clips.
    Returns a list of clip candidates with start/end times.
    """
    segments = transcript.get("segments", [])
    if not segments:
        raise ValueError("No transcript segments found")

    total_duration = segments[-1]["end"] if segments else 0
    if total_duration < CLIP_MIN_SECONDS:
        raise ValueError(f"Video too short ({total_duration:.0f}s). Need at least {CLIP_MIN_SECONDS}s.")

    # Build compact transcript for GPT (with timestamps)
    transcript_text = _build_transcript_text(segments)

    if OPENAI_API_KEY:
        return await _select_with_gpt(transcript_text, segments, total_duration)
    else:
        return _select_heuristically(segments, total_duration)


def _build_transcript_text(segments: List[Dict]) -> str:
    lines = []
    for seg in segments:
        t = f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}"
        lines.append(t)
    return "\n".join(lines)


async def _select_with_gpt(transcript_text: str, segments: List[Dict], total_duration: float) -> List[Dict]:
    """Use GPT-4o to intelligently select clips."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    system_prompt = """You are an expert educational content curator for Class 9 students (ages 13-15).
Your job is to identify the BEST short educational clips from a video transcript.

SELECTION CRITERIA (score each window):
1. Hook strength (0-10): Does it open with a question, bold statement, or surprising fact?
2. Educational clarity (0-10): Is one concept explained simply? No jargon without explanation?
3. Engagement (0-10): Is the tone energetic? Are key words emphasized? Is it memorable?
4. Self-contained (0-10): Can a student understand it WITHOUT seeing the rest of the video?
5. Class 9 relevance (0-10): Matches NCERT curriculum or general school concepts?

RULES:
- Each clip must be 20-60 seconds long
- Select exactly 3-5 non-overlapping clips
- Prefer moments with clear explanations and natural stopping points
- Avoid clips that start/end mid-sentence

Respond with ONLY valid JSON, no markdown, no explanation:
{
  "clips": [
    {
      "start": 12.5,
      "end": 45.0,
      "hook_score": 8,
      "clarity_score": 9,
      "engagement_score": 7,
      "reason": "Explains Newton's first law with a real-life example"
    }
  ]
}"""

    user_message = f"""Video duration: {total_duration:.1f} seconds
Clip requirements: {CLIP_MIN_SECONDS}-{CLIP_MAX_SECONDS} seconds each, select {NUM_CLIPS} clips maximum.

TRANSCRIPT:
{transcript_text[:6000]}"""  # Limit to ~6000 chars to stay within token limits

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    clips = data.get("clips", [])

    # Validate and clamp timestamps
    valid_clips = []
    for clip in clips:
        start = max(0.0, float(clip["start"]))
        end = min(total_duration, float(clip["end"]))
        duration = end - start
        if CLIP_MIN_SECONDS <= duration <= CLIP_MAX_SECONDS:
            clip["start"] = round(start, 2)
            clip["end"] = round(end, 2)
            clip["duration"] = round(duration, 2)
            valid_clips.append(clip)

    if not valid_clips:
        # Fallback to heuristic if GPT returned nothing valid
        return _select_heuristically([], total_duration, segments)

    return valid_clips[:NUM_CLIPS]


def _select_heuristically(segments: List[Dict], total_duration: float, all_segments: List[Dict] = None) -> List[Dict]:
    """Fallback: evenly-spaced clips when no API key is available."""
    segs = all_segments or segments
    if not segs:
        # Pure time-based split
        step = total_duration / 5
        clips = []
        for i in range(min(NUM_CLIPS, 5)):
            start = i * step + 5
            end = start + 40
            if end <= total_duration:
                clips.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": 40.0,
                    "reason": f"Segment {i+1} (heuristic selection)",
                    "hook_score": 5,
                    "clarity_score": 5,
                    "engagement_score": 5,
                })
        return clips

    # Group segments into ~40-second windows
    clips = []
    window_start = None
    window_text = []
    window_duration = 0

    for seg in segs:
        if window_start is None:
            window_start = seg["start"]

        window_text.append(seg["text"])
        window_duration = seg["end"] - window_start

        if window_duration >= 35:
            clips.append({
                "start": round(window_start, 2),
                "end": round(seg["end"], 2),
                "duration": round(window_duration, 2),
                "reason": "Heuristic segment (no API key)",
                "hook_score": 5,
                "clarity_score": 5,
                "engagement_score": 5,
            })
            window_start = None
            window_text = []
            window_duration = 0

            if len(clips) >= NUM_CLIPS:
                break

    return clips
