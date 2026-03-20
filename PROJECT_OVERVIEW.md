# 🎬 Cinematic Text-To-Video AI Tool — Complete Project Overview

> **Single source of truth for the entire project.**
> This file merges previously separate guides (README, templates) into one document so any AI assistant or developer can fully understand the **newly simplified, visually-focused** project at a glance.

---

## 📌 What This Project Does

This is a **fully automated, visually-focused cinematic video generator** that:

1. Takes a **Simple Description** (topic) OR a **Direct JSON Script** (director's vision) as input.
2. If a simple description is given, uses an **LLM (Gemini)** via the `cinematic_broll_generator` to expand it into a fully structured, multi-scene visual storyboard.
3. Automatically maps timestamps and visual cues to download **highly relevant background videos** from Pexels stock.
4. Renders and concatenates the final **silent MP4 video** sequence using FFmpeg (audio and voiceovers have been explicitly removed to focus on visual B-Roll generation).
5. Provides a stunning **"Hollywood Noir & Amber" UI** to build your videos with one click.

**Output:** A high-quality MP4 video tailored to the exact timing of your scene descriptions — ready for YouTube Shorts, Instagram Reels, or TikTok.

---

## 🗂️ Project Structure

```
Text-To-Video-AI-Tool/
│
├── web_app.py                # FastAPI web server + REST API (The core engine)
│
├── static/
│   ├── index.html            # Web UI frontend (Noir & Amber Cinematic theme)
│   ├── styles.css            # UI styles 
│   └── script.js             # UI JavaScript logic (Simple & Direct modes)
│
├── utility/
│   ├── config.py             # Central config — reads .env, validates keys
│   ├── utils.py              # Shared helpers
│   │
│   ├── script/
│   │   └── cinematic_broll_generator.py # Transforms simple text into Director's JSON
│   │
│   ├── video/
│   │   ├── background_video_generator.py    # Fetches Pexels videos/images
│   │   ├── video_search_query_generator.py  # Maps script to timed search queries
│   │   └── youtube_uploader.py              # Uploads video to YouTube via OAuth
│   │
│   └── render/
│       ├── render_engine.py            # Main render coordinator
│       └── ffmpeg_render_engine.py     # Pure FFmpeg renderer (Video only)
│
├── .env                      # Your local API keys and configuration
├── requirements.txt          # All Python dependencies
└── client_secrets.json       # (Optional) Google OAuth credentials for YouTube upload
```

---

## 🚀 How to Run (Web Native)

### Start the Web Server
The UI has been massively overhauled to be the primary interface. You should use the local server:

```bash
# Activate virtual environment
source .venv/bin/activate       # macOS/Linux
.venv\Scripts\activate          # Windows

# Start FastAPI
uvicorn web_app:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

The Web UI supports:
- ✨ **Simple Description mode**: Type a basic idea ("A futuristic city"), and the AI expands it.
- 📝 **Direct Script mode**: Paste raw JSON to control exactly what the engine fetches.
- ⏱️ **Duration**: 10s, 30s, or 60s clips.

---

## 🔧 Configuration (.env file)

Your `.env` file requires only the absolute essentials now that voice/TTS bloat is removed:

```env
# ── LLM Provider (For expanding Simple Descriptions) ──
LLM_PROVIDER=gemini               
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash

# ── Pexels (For fetching Background Video) ──
PEXELS_API_KEY=your_key_here

# ── Video Output ──
VIDEO_ORIENTATION=portrait        # portrait (1080x1920) or landscape (1920x1080)
```

---

## 🌐 Web API Endpoints

The FastAPI server exposes these simplified endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the web UI |
| `POST` | `/generate` | Generate the silent B-Roll visual sequence video |
| `GET` | `/download/{file_name}` | Download generated video |
| `POST` | `/upload-youtube` | Upload `rendered_video.mp4` to YouTube |

---

## 🎬 Direct Script Template (The "Director's Vision")

When you select **"Direct Script"** in the UI, you bypass the AI generator and pass raw JSON. This tells the system *exactly* what lighting, camera movement, and artistic style to apply to each scene.

### The JSON Structure
Your payload should look exactly like this:
```json
{
  "scenes": [
    {
      "visual_prompt": "A woman in a shimmering red silk saree is lighting traditional clay diyas on a balcony.",
      "duration": 5,
      "keyword_hints": ["cinematic", "golden hour", "bokeh"]
    },
    {
      "visual_prompt": "Close-up tracking shot on joyful faces covered in exploding colorful gulal powder.",
      "duration": 10,
      "keyword_hints": ["slow motion", "high saturation", "fluid"]
    }
  ]
}
```

### The Formula for a Perfect Scene Prompt
To get high-quality matches, write your "visual_prompt" following this structure:
**[Subject] + [Action] + [Setting/Background] + [Camera Movement/Angle] + [Lighting & Style]**

### Example Direct Prompts for Inspiration

**🪔 Diwali (Festival of Lights)**
> "A breathtaking 3D animation of a home at dusk during Diwali. A woman in a shimmering silk saree is lighting a row of traditional clay diyas on a balcony. In the background, the night sky is filled with distant, colorful fireworks."

**💃 Navratri / Durga Puja**
> "A vibrant, fast-paced animation of a Garba dance circle during Navratri. Women in colorful embroidered Chaniya Cholis with mirror-work are spinning rapidly, their skirts creating a blur of color. Dramatic theatrical lighting, rhythmic movement."

### Top 5 Technical Modifier Keywords (Use in "keyword_hints"):
1. **For Realism:** `Cinematic`, `hyper-realistic`, `8k resolution`, `photorealistic`, `depth of field`
2. **For 3D Animation:** `Pixar style`, `Unreal Engine 5`, `octane render`, `raytracing`
3. **For Camera Motion:** `Slow pan`, `tracking shot`, `drone shot`, `handheld camera style`
4. **For Lighting:** `Golden hour`, `neon cyberpunk lighting`, `volumetric fog`, `god rays`
5. **For Mood:** `Epic`, `serene`, `highly energetic`, `moody and atmospheric`

---

## 🗑️ Files to Ignore / Not Commit

```text
.env                    # Contains real API keys — NEVER commit
.venv/                  # Virtual environment
.logs/                  # Runtime API logs
rendered_video.mp4      # Generated output
client_secrets.json     # Google OAuth credentials — NEVER commit
__pycache__/
```

---

*Last updated: March 2026 | Project: Text-To-Video-AI-Tool (Cinematic Visual Update)*
