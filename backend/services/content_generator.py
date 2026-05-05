import os
import json
import asyncio
from typing import List, Dict

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def generate_content(clips: List[Dict], transcript: Dict) -> List[Dict]:
    """
    Generate title, description, and thumbnail concept for each clip.
    Falls back to template-based generation if no API key.
    """
    segments = transcript.get("segments", [])

    tasks = []
    for clip in clips:
        # Extract clip transcript
        clip_text = _get_clip_text(segments, clip["start"], clip["end"])
        clip["clip_text"] = clip_text
        tasks.append(_generate_for_clip(clip, clip_text))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (clip, result) in enumerate(zip(clips, results)):
        if isinstance(result, Exception):
            # Fallback content on error
            clip["title"] = f"Educational Clip {clip['clip_num']}"
            clip["description"] = clip.get("reason", "An educational moment from this video.")
            clip["thumbnail_text"] = "Learn This!"
            clip["hashtags"] = "#Education #Class9 #Learning #Students #Study"
        else:
            clip.update(result)

    return clips


def _get_clip_text(segments: List[Dict], start: float, end: float) -> str:
    """Extract transcript text for a clip's time range."""
    texts = []
    for seg in segments:
        if seg["end"] < start or seg["start"] > end:
            continue
        texts.append(seg["text"].strip())
    return " ".join(texts)


async def _generate_for_clip(clip: Dict, clip_text: str) -> Dict:
    """Generate metadata for a single clip."""
    if OPENAI_API_KEY:
        return await _generate_with_gpt(clip, clip_text)
    else:
        return _generate_template(clip, clip_text)


async def _generate_with_gpt(clip: Dict, clip_text: str) -> Dict:
    """Use GPT-4o to generate engaging student-friendly content."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    system_prompt = """You are a creative content writer for Indian Class 9 students (ages 13-15).
You create simple, engaging, and relatable content about educational topics.

Your writing style:
- Use simple English that 14-year-olds can easily understand
- Use exciting words, emojis where appropriate
- Make students CURIOUS and excited to learn
- Short sentences. Punchy. Direct.
- Reference NCERT subjects when relevant (Science, Maths, Social Science, English)

Respond with ONLY valid JSON, no markdown:
{
  "title": "Under 60 chars, catchy, student-friendly title",
  "description": "2-3 sentences explaining what this clip teaches. Simple language. End with a hook.",
  "thumbnail_text": "Bold 3-5 word text for thumbnail overlay",
  "hashtags": "#Science #Class9 #CBSE (5 relevant hashtags)"
}"""

    user_message = f"""Create content for this educational video clip:

Clip transcript: {clip_text[:1500]}
Reason selected: {clip.get('reason', 'Strong educational content')}
Duration: {clip.get('duration', 30):.0f} seconds"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=300,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    return {
        "title": data.get("title", f"Educational Clip {clip['clip_num']}"),
        "description": data.get("description", ""),
        "thumbnail_text": data.get("thumbnail_text", "Learn This!"),
        "hashtags": data.get("hashtags", "#Education #Class9 #Learning"),
    }


def _generate_template(clip: Dict, clip_text: str) -> Dict:
    """Template-based fallback when no API key is set."""
    reason = clip.get("reason", "")
    clip_num = clip.get("clip_num", 1)

    # Simple keyword extraction
    words = clip_text.split()
    keywords = [w for w in words if len(w) > 5][:3]
    topic = " ".join(keywords[:2]) if keywords else "this concept"

    titles = [
        f"This Is What You Need to Know About {topic.title()}",
        f"Class 9 Students Must Know This! 🎯",
        f"The Simplest Explanation of {topic.title()}",
        f"Why {topic.title()} Matters — Explained Simply",
        f"Understand {topic.title()} in Under a Minute!",
    ]

    descriptions = [
        f"This clip covers an important concept that every Class 9 student should understand. {reason} Watch till the end for the key takeaway!",
    ]

    return {
        "title": titles[(clip_num - 1) % len(titles)],
        "description": descriptions[0],
        "thumbnail_text": "Must Know! 📚",
        "hashtags": "#Education #Class9 #CBSE #Learning #Students",
    }
