# 🎬 EduClips — AI Video Clip Generator for Class 9 Students

> Upload a long lecture video → AI automatically generates 3–5 short, engaging educational clips with titles, descriptions, and subtitles.

![EduClips Demo](https://via.placeholder.com/900x400/6C63FF/FFFFFF?text=EduClips+AI+%7C+Turn+Lectures+into+Reels)

##  What It Does

1. **Upload** any lecture video (MP4, MOV, AVI, WEBM — up to 500MB)
2. **Whisper AI** transcribes the entire audio with timestamps
3. **GPT-4o** scores every 30–60 second segment for hook strength, clarity, and educational value
4. **FFmpeg** cuts the best clips and exports them in:
   -  Vertical (9:16) for Instagram Reels & YouTube Shorts
   -  Horizontal (16:9) for YouTube
5. **Subtitles** are automatically burned into both formats
6. **AI generates** a student-friendly title, description, and thumbnail concept for each clip

---

##  Project Structure

```
educlips/
├── backend/
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt          # Python dependencies
│   ├── routers/
│   │   └── clips.py              # Upload & status endpoints
│   ├── services/
│   │   ├── audio_extractor.py    # FFmpeg audio extraction
│   │   ├── transcriber.py        # Whisper speech-to-text
│   │   ├── clip_selector.py      # GPT-4o clip scoring
│   │   ├── video_processor.py    # FFmpeg clip cutting + subtitles
│   │   └── content_generator.py  # GPT-4o titles & descriptions
│   └── utils/
│       ├── job_store.py          # In-memory job tracking
│       └── cleanup.py            # Auto-cleanup old files
├── frontend/
│   ├── templates/
│   │   └── index.html            # Main web UI
│   └── static/
│       ├── css/style.css         # Stylesheet
│       └── js/app.js             # Frontend JavaScript
├── scripts/
│   └── run_local.sh              # Local development runner
├── Dockerfile                    # For Railway / Docker deploy
├── render.yaml                   # Render.com configuration
├── .env.example                  # Environment variable template
└── README.md
```

---

## Quick Start (Local)

### Prerequisites

- Python 3.10+
- FFmpeg installed
- OpenAI API key

### 1. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

**Windows:**
Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add to PATH.

### 2. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/educlips.git
cd educlips
```

### 3. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
nano .env
```

Your `.env` file should look like:
```
OPENAI_API_KEY=sk-your-key-here
USE_OPENAI_API=true
NUM_CLIPS=5
```

### 4. Run Locally

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

Or manually:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at: **http://localhost:8000**

---

##  Deployment (Free Tier)

### Option A: Render.com (Recommended — Free)

1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial EduClips commit"
   git remote add origin https://github.com/YOUR_USERNAME/educlips.git
   git push -u origin main
   ```

2. Go to [render.com](https://render.com) → **New** → **Web Service**

3. Connect your GitHub repo

4. Configure:
   - **Root Directory:** `backend`
   - **Build Command:** `apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

5. Add Environment Variables:
   - `OPENAI_API_KEY` = your key
   - `USE_OPENAI_API` = `true`
   - `NUM_CLIPS` = `5`

6. Deploy → Your app is live at `https://your-app.onrender.com` 🎉

> **Note:** The free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds to wake up.

---

### Option B: Railway.app

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. Deploy:
   ```bash
   railway init
   railway up
   ```

3. Set environment variables in the Railway dashboard

4. Your app gets a URL like `https://educlips-production.up.railway.app`

---

### Option C: Docker (Any Cloud)

```bash
# Build
docker build -t educlips .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key \
  -e USE_OPENAI_API=true \
  educlips
```

Deploy this container to:
- **Google Cloud Run** (pay-per-request)
- **AWS ECS** (scalable)
- **DigitalOcean App Platform** ($5/month)

---

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload video, returns `job_id` |
| `GET` | `/api/status/{job_id}` | Poll processing status |
| `DELETE` | `/api/job/{job_id}` | Clean up a completed job |
| `GET` | `/health` | Health check |

### Upload Response
```json
{
  "job_id": "uuid-here",
  "message": "Processing started",
  "filename": "lecture.mp4"
}
```

### Status Response (completed)
```json
{
  "job_id": "uuid-here",
  "status": "completed",
  "progress": 100,
  "message": "Done! Generated 5 clips.",
  "clips": [
    {
      "clip_num": 1,
      "start": 45.5,
      "end": 98.2,
      "duration": 52.7,
      "title": "Why Newton's First Law Matters ",
      "description": "This clip explains Newton's First Law with a real-life car example...",
      "thumbnail_text": "Objects in Motion!",
      "hashtags": "#Physics #Class9 #CBSE #Newton #Science",
      "hook_score": 9,
      "clarity_score": 8,
      "engagement_score": 7,
      "horizontal_path": "outputs/uuid/clip_1/clip_horizontal.mp4",
      "vertical_path": "outputs/uuid/clip_1/clip_vertical.mp4"
    }
  ]
}
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | Your OpenAI API key |
| `USE_OPENAI_API` | `true` | Use hosted Whisper API (vs local) |
| `NUM_CLIPS` | `5` | Max number of clips to generate |
| `CLIP_MIN_SECONDS` | `20` | Minimum clip duration |
| `CLIP_MAX_SECONDS` | `60` | Maximum clip duration |

---

##  Cost Estimate

For a **60-minute lecture video**:

| Service | Cost |
|---------|------|
| Whisper API (transcription) | ~$0.36 |
| GPT-4o (clip selection) | ~$0.20 |
| GPT-4o (5× content generation) | ~$0.05 |
| FFmpeg processing | Free |
| **Total per video** | **~$0.61** |

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Video Processing | FFmpeg |
| Speech-to-Text | OpenAI Whisper API |
| Clip Selection | OpenAI GPT-4o |
| Content Generation | OpenAI GPT-4o |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Deployment | Render / Railway / Docker |

---

##  Contributing

Pull requests welcome! Especially interested in:
- Face detection for smarter 9:16 cropping (MediaPipe)
- Background music auto-mixing
- YouTube direct upload integration
- Support for regional Indian languages

---

##  License

MIT License — use freely for educational purposes.

---

Built with ❤️ for Class 9 students across India 🇮🇳
