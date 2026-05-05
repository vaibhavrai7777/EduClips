import os
import uuid
import shutil
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager

from routers import clips
from utils.cleanup import schedule_cleanup

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield
    # Shutdown cleanup


app = FastAPI(
    title="EduClips API",
    description="AI-powered educational video clip generator for Class 9 students",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static output files
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Include routers
app.include_router(clips.router, prefix="/api", tags=["clips"])


@app.get("/")
async def root():
    return FileResponse("../frontend/templates/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "message": "EduClips API is running"}
