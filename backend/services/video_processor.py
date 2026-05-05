import os
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict


async def process_clips(
    video_path: Path,
    clips: List[Dict],
    transcript: Dict,
    output_dir: Path,
) -> List[Dict]:
    """
    For each clip:
    1. Cut the video segment
    2. Export vertical (9:16) and horizontal (16:9) versions
    3. Burn subtitles
    Returns updated clip list with file paths.
    """
    segments = transcript.get("segments", [])
    processed = []

    for i, clip in enumerate(clips):
        clip_num = i + 1
        start = clip["start"]
        end = clip["end"]
        clip_dir = output_dir / f"clip_{clip_num}"
        clip_dir.mkdir(exist_ok=True)

        # Build subtitle file for this clip's time range
        srt_path = clip_dir / "subtitles.srt"
        _write_srt(segments, start, end, srt_path)

        # Export horizontal (16:9) with subtitles
        horizontal_path = clip_dir / "clip_horizontal.mp4"
        await _export_horizontal(video_path, start, end, srt_path, horizontal_path)

        # Export vertical (9:16) with subtitles
        vertical_path = clip_dir / "clip_vertical.mp4"
        await _export_vertical(video_path, start, end, srt_path, vertical_path)

        # Generate thumbnail
        thumb_path = clip_dir / "thumbnail.jpg"
        await _extract_thumbnail(horizontal_path, thumb_path)

        clip["clip_num"] = clip_num
        clip["horizontal_path"] = str(horizontal_path.relative_to(output_dir.parent))
        clip["vertical_path"] = str(vertical_path.relative_to(output_dir.parent))
        clip["thumbnail_path"] = str(thumb_path.relative_to(output_dir.parent))
        clip["srt_path"] = str(srt_path.relative_to(output_dir.parent))
        processed.append(clip)

    return processed


def _write_srt(segments: List[Dict], clip_start: float, clip_end: float, srt_path: Path):
    """Generate SRT subtitle file for a clip, adjusted to clip-relative timestamps."""
    srt_lines = []
    idx = 1

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]

        # Only include segments within the clip window
        if seg_end < clip_start or seg_start > clip_end:
            continue

        # Clamp to clip boundaries
        rel_start = max(0.0, seg_start - clip_start)
        rel_end = min(clip_end - clip_start, seg_end - clip_start)
        text = seg["text"].strip()

        if not text:
            continue

        srt_lines.append(str(idx))
        srt_lines.append(f"{_fmt_time(rel_start)} --> {_fmt_time(rel_end)}")
        srt_lines.append(text)
        srt_lines.append("")
        idx += 1

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")


def _fmt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def _export_horizontal(
    video_path: Path, start: float, end: float,
    srt_path: Path, output_path: Path
):
    """Export 16:9 horizontal clip with burned subtitles."""
    duration = end - start
    subtitle_filter = _build_subtitle_filter(srt_path)

    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-t", str(duration),
        "-i", str(video_path),
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path),
    ]

    await _run_ffmpeg(cmd, f"horizontal clip export ({start:.1f}s-{end:.1f}s)")


async def _export_vertical(
    video_path: Path, start: float, end: float,
    srt_path: Path, output_path: Path
):
    """Export 9:16 vertical clip (1080x1920) with burned subtitles."""
    duration = end - start

    # Crop to square from center, then scale to 1080x1920
    # Detect input resolution for smart cropping
    crop_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
    )
    subtitle_filter = _build_subtitle_filter(srt_path)
    full_filter = f"{crop_filter},{subtitle_filter}"

    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-t", str(duration),
        "-i", str(video_path),
        "-vf", full_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path),
    ]

    await _run_ffmpeg(cmd, f"vertical clip export ({start:.1f}s-{end:.1f}s)")


def _build_subtitle_filter(srt_path: Path) -> str:
    """Build FFmpeg subtitle filter with styled captions."""
    # Escape special characters in path
    safe_path = str(srt_path).replace("\\", "/").replace(":", "\\:")
    return (
        f"subtitles='{safe_path}':force_style="
        "'FontName=Arial,FontSize=20,PrimaryColour=&HFFFFFF,"
        "OutlineColour=&H000000,Outline=2,Shadow=1,"
        "Alignment=2,MarginV=30'"
    )


async def _extract_thumbnail(video_path: Path, thumb_path: Path):
    """Extract a frame from 2 seconds in as thumbnail."""
    cmd = [
        "ffmpeg",
        "-ss", "2",
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        "-y",
        str(thumb_path),
    ]
    try:
        await _run_ffmpeg(cmd, "thumbnail extraction")
    except Exception:
        pass  # Non-critical, skip if fails


async def _run_ffmpeg(cmd: List[str], description: str):
    """Run an FFmpeg command asynchronously."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed ({description}): {stderr.decode()[-500:]}")
