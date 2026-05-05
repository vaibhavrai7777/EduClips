import os
import uuid
import shutil
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from services.transcriber import transcribe_audio
from services.clip_selector import select_clips
from services.video_processor import process_clips
from services.content_generator import generate_content
from services.audio_extractor import extract_audio
from utils.job_store import job_store

router = APIRouter()

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    clips: Optional[list] = None
    error: Optional[str] = None


@router.post("/upload", response_model=dict)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload a video and start async processing."""
    allowed_types = ["video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: mp4, mpeg, mov, avi, webm"
        )

    max_size = 500 * 1024 * 1024  # 500MB
    job_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    # Save uploaded file
    try:
        with open(video_path, "wb") as buffer:
            content = await file.read()
            if len(content) > max_size:
                raise HTTPException(status_code=413, detail="File too large. Max 500MB.")
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Initialize job
    job_store.set(job_id, {
        "status": "queued",
        "progress": 0,
        "message": "Video uploaded. Starting pipeline...",
        "clips": None,
        "error": None,
    })

    # Start background processing
    background_tasks.add_task(run_pipeline, job_id, video_path)

    return {"job_id": job_id, "message": "Processing started", "filename": file.filename}


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    """Poll the status of a processing job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(job_id=job_id, **job)


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Clean up a completed job and its files."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove output directory
    output_path = OUTPUT_DIR / job_id
    if output_path.exists():
        shutil.rmtree(output_path)

    # Remove upload files
    for f in UPLOAD_DIR.glob(f"{job_id}_*"):
        f.unlink(missing_ok=True)

    job_store.delete(job_id)
    return {"message": "Job deleted successfully"}


async def run_pipeline(job_id: str, video_path: Path):
    """Full async pipeline: extract → transcribe → select → process → generate."""
    output_dir = OUTPUT_DIR / job_id
    output_dir.mkdir(exist_ok=True)

    try:
        # Step 1: Extract audio
        job_store.update(job_id, {"status": "processing", "progress": 10, "message": "Extracting audio from video..."})
        audio_path = await extract_audio(video_path, output_dir)

        # Step 2: Transcribe
        job_store.update(job_id, {"progress": 25, "message": "Transcribing speech with Whisper AI..."})
        transcript = await transcribe_audio(audio_path)

        # Step 3: Select clips
        job_store.update(job_id, {"progress": 45, "message": "AI selecting best educational clips..."})
        selected_clips = await select_clips(transcript)

        if not selected_clips:
            raise ValueError("No suitable clips found in video. Try a longer or clearer video.")

        # Step 4: Process video clips
        job_store.update(job_id, {"progress": 65, "message": f"Cutting and formatting {len(selected_clips)} clips..."})
        processed_clips = await process_clips(video_path, selected_clips, transcript, output_dir)

        # Step 5: Generate AI content
        job_store.update(job_id, {"progress": 85, "message": "Generating titles, descriptions, and thumbnails..."})
        final_clips = await generate_content(processed_clips, transcript)

        # Done
        job_store.update(job_id, {
            "status": "completed",
            "progress": 100,
            "message": f"Done! Generated {len(final_clips)} clips.",
            "clips": final_clips,
        })

    except Exception as e:
        job_store.update(job_id, {
            "status": "failed",
            "progress": 0,
            "message": "Pipeline failed.",
            "error": str(e),
        })

    finally:
        # Clean up upload file to save disk space
        if video_path.exists():
            video_path.unlink(missing_ok=True)
        # Clean up audio file
        audio_path_check = output_dir / "audio.wav"
        if audio_path_check.exists():
            audio_path_check.unlink(missing_ok=True)
