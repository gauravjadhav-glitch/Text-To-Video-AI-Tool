import os
import uuid
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from utility.script.script_generator import generate_script
from utility.script.viral_shorts_generator import generate_viral_short, extract_voiceover_script
from utility.script.visual_prompt_generator import generate_visual_prompts, generate_video_search_keywords
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from utility.config import get_config

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for the Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, you can restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Map language input to the correct EdgeTTS voices
VOICE_MAP = {
    "marathi": "mr-IN-AarohiNeural",
    "hindi": "hi-IN-MadhurNeural",
    "english": "en-AU-WilliamNeural",
    "english-premium": "coral", # OpenAI.fm (gpt-4o-mini-tts)
    "english-pro": "shimmer" # OpenAI.fm (gpt-4o-mini-tts)
}

# Map language input to the correct Whisper language codes
STT_LANG_MAP = {
    "marathi": "mr",
    "hindi": "hi",
    "english": "en",
    "english-premium": "en",
    "english-pro": "en"
}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


async def _generate_video_core(
    *,
    input_text: str,
    duration: int,
    input_type: str,
):
    request_id = uuid.uuid4().hex[:8]
    config = get_config()
    orientation_landscape = config.get_video_orientation()
    
    input_text = input_text.strip()
    if not input_text:
        raise ValueError("Input cannot be empty")
        
    VIDEO_SERVER = "pexel"  # Use real Pexels video clips for cinematic output

    if input_type == "simple":
        # We need to run the simple description through the Cinematic B-Roll Transformer
        from utility.script.cinematic_broll_generator import generate_cinematic_broll_script
        print(f"[TRANSFORMER] Generating internal script from simple prompt...")
        script_data = generate_cinematic_broll_script(input_text, duration=duration)
    else:
        print("[DIRECT] Using provided text as direct script input.")
        # direct script string is probably json string, we attempt to parse it
        import json
        try:
            script_data = json.loads(input_text)
        except Exception:
            # Fallback if they just passed plain text, create a dummy structure
            script_data = {
                "scenes": [
                    {
                        "visual_prompt": input_text,
                        "duration": duration,
                        "keyword_hints": ["cinematic", "beautiful"]
                    }
                ]
            }
            
    # Now we have script_data["scenes"] with durations and visual keywords
    total_duration = 0
    search_terms = []
    
    for scene in script_data.get("scenes", []):
        scene_dur = float(scene.get("duration", 5))
        queries = [scene.get("visual_prompt", "cinematic scene")]
        queries.extend(scene.get("keyword_hints", []))
        
        search_terms.append([[total_duration, total_duration + scene_dur], queries])
        total_duration += scene_dur
        
    if total_duration == 0:
        # Fallback if parsing returned 0 sec
        search_terms.append([[0, duration], [input_text]])
        total_duration = duration
        
    print(f"[TIMING] Total duration: {total_duration}")

    # Fetch Media
    if search_terms:
        background_video_urls = await generate_video_url(
            search_terms, VIDEO_SERVER, orientation_landscape=orientation_landscape
        )
    else:
        background_video_urls = None

    background_video_urls = merge_empty_intervals(background_video_urls)

    if not background_video_urls:
        raise RuntimeError("No background videos/images generated.")

    # Compositing final video with None for audio and None for timed_captions
    print("[RENDER] Compositing final video without audio capabilities.")
    video_file_path = get_output_media(None, None, background_video_urls, VIDEO_SERVER)

    return {
        "video_file_path": video_file_path,
        "script_used": script_data,
        "video_server": VIDEO_SERVER,
    }



@app.post("/generate")
async def generate_video(
    input_text: str = Form(...),
    duration: int = Form(30),
    input_type: str = Form("simple"),
):
    try:
        result = await _generate_video_core(
            input_text=input_text,
            duration=duration,
            input_type=input_type,
        )
        return JSONResponse(
            {
                "status": "success",
                "video_url": f"/download/{result['video_file_path']}",
                "script_used": result["script_used"],
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/download/{file_name}")
async def download_video(file_name: str):
    if os.path.exists(file_name):
        return FileResponse(file_name, media_type="video/mp4", filename=file_name)
    return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)


@app.post("/upload-youtube")
async def upload_youtube(
    file_name: str = Form("rendered_video.mp4"),
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    privacy_status: str = Form("public"),
):
    """
    Upload an existing rendered mp4 to YouTube using local OAuth.
    Requires `client_secrets.json` in repo root.
    """
    try:
        from utility.video.youtube_uploader import upload_video

        file_name = (file_name or "").strip()
        if not file_name:
            return JSONResponse({"status": "error", "message": "file_name is required"}, status_code=400)

        if not os.path.exists(file_name):
            return JSONResponse({"status": "error", "message": f"File not found: {file_name}"}, status_code=404)

        title = (title or "").strip()
        if not title:
            return JSONResponse({"status": "error", "message": "title is required"}, status_code=400)

        privacy_status = (privacy_status or "public").strip().lower()
        if privacy_status not in ["private", "unlisted", "public"]:
            return JSONResponse(
                {"status": "error", "message": "privacy_status must be private|unlisted|public"},
                status_code=400,
            )

        tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

        # OAuth + upload are blocking; offload to a worker thread
        video_id = await asyncio.to_thread(
            upload_video,
            file_name,
            title,
            description,
            tag_list,
            "27",
            privacy_status,
        )
        return JSONResponse({"status": "success", "video_id": video_id})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
