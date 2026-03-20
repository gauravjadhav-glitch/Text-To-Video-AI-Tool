# 🎬 Cinematic Text-To-Video AI Tool

> **Visually-focused AI video generator** — turn any topic or Direct Script into a stunning sequence of B-Roll videos in seconds.

## 📖 Full Documentation

**→ See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for the complete guide**

It covers everything in one place:
- What this project does (Cinematic B-Roll Generator)
- Full project structure
- How to run the Web App
- The required `.env` options (now heavily simplified!)
- API endpoints reference
- The Direct Script (JSON) format explained
- Detailed examples for festival prompt generation
- All required API keys

## ⚡ Quick Start (Web App Recommended)

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Start the FastAPI web app
uvicorn web_app:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000` in your browser.

*Note: Generating via the python CLI `app.py` is possible but legacy; the fastest way to experience the new AI Director's Vision is via the web app console.*

Output: `rendered_video.mp4`
