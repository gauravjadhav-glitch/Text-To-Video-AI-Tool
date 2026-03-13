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
    mode: str,
    duration: int,
    language: str,
    use_ai_images: bool,
    use_stock_images: bool,
):
    # Use unique filenames per request to prevent race conditions
    request_id = uuid.uuid4().hex[:8]
    SAMPLE_FILE_NAME = f"audio_tts_{request_id}.wav"

    is_documentary = (mode == "documentary")

    # Documentary uses Pexels stock videos for realistic footage
    if is_documentary:
        VIDEO_SERVER = "pexel"
    elif use_ai_images:
        VIDEO_SERVER = "stable_diffusion"
    elif use_stock_images:
        VIDEO_SERVER = "pexels_image"
    else:
        VIDEO_SERVER = "pexel"

    # Use OpenAI TTS for documentary (natural narrator) and premium voices
    if is_documentary or language.lower() in ["english-premium", "english-pro"]:
        tts_provider_override = "openai"
    else:
        tts_provider_override = None

    config = get_config()
    orientation_landscape = config.get_video_orientation()

    input_text = input_text.strip()
    if not input_text:
        raise ValueError("Input cannot be empty")

    # 1. Generate Script
    viral_data = None
    if is_documentary:
        print(f"[DOCUMENTARY] Generating script for: {input_text} ({duration}s, lang={language})")
        response = generate_script(
            topic=input_text,
            duration=duration,
            mode="documentary",
        )
        print(f"[DOCUMENTARY] Script generated: {response[:100]}...")
        # Use user-selected language instead of hardcoding Hindi
        if language.lower() not in VOICE_MAP:
            language = "hindi"
        voice = VOICE_MAP.get(language.lower(), "hi-IN-MadhurNeural")
        # Use OpenAI voice for documentary if using OpenAI TTS
        if tts_provider_override == "openai":
            voice = "onyx"
    elif mode == "viral":
        print(f"[VIRAL] Generating viral Shorts script for: {input_text}")
        viral_data = generate_viral_short(topic=input_text, duration=duration, language=language)
        response   = extract_voiceover_script(viral_data)
        if not response or not response.strip():
            raise ValueError("Failed to extract voiceover script from viral data")
        print(f"[VIRAL] Voiceover extracted ({len(response.split())} words): {response[:80]}...")
    elif mode == "topic":
        response = generate_script(
            f"Write a {duration} second script in {language} about: {input_text}",
            duration=duration,
        )
    else:
        response = input_text

    if not response or not response.strip():
        raise ValueError("Script generation returned empty content")

    # 2. Get correct voice and STT language
    if not is_documentary:
        voice = VOICE_MAP.get(language.lower(), "mr-IN-AarohiNeural")
    stt_lang = STT_LANG_MAP.get(language.lower(), "mr")

    # 3. Generate Audio
    if tts_provider_override:
        original_provider = os.getenv("TTS_PROVIDER")
        os.environ["TTS_PROVIDER"] = tts_provider_override
        try:
            await generate_audio(response, SAMPLE_FILE_NAME, voice=voice)
        finally:
            if original_provider:
                os.environ["TTS_PROVIDER"] = original_provider
            else:
                os.environ.pop("TTS_PROVIDER", None)
    else:
        await generate_audio(response, SAMPLE_FILE_NAME, voice=voice)

    # 3b. Get actual audio duration for accurate video segment timing
    import subprocess as _sp
    try:
        _probe = _sp.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", SAMPLE_FILE_NAME],
            capture_output=True, text=True, timeout=10
        )
        actual_audio_duration = float(_probe.stdout.strip())
        print(f"[AUDIO] Actual audio duration: {actual_audio_duration:.2f}s")
    except Exception:
        actual_audio_duration = None
        print("[AUDIO] Could not probe audio duration, will use caption timing")

    # 4. Extract Timed Captions (use transcribe, NOT translate, to keep original language)
    from utility.stt.whisper_stt import generate_timed_captions as whisper_stt

    timed_captions = whisper_stt(SAMPLE_FILE_NAME, model_size="tiny", language=stt_lang)

    if not timed_captions:
        raise RuntimeError("Speech-to-text returned no captions")

    # 4b. Determine total duration — prefer actual audio duration over caption timing
    caption_end = max(tc[0][1] if isinstance(tc[0], (list, tuple)) else tc[0] for tc in timed_captions)
    total_duration = actual_audio_duration if actual_audio_duration else caption_end
    print(f"[TIMING] Using total_duration={total_duration:.2f}s (audio={actual_audio_duration}, caption_end={caption_end:.2f})")

    # 5. Create Search Queries / Visual Prompts Map
    if is_documentary:
        print("[DOCUMENTARY] Generating video search keywords from script...")
        import re as re_mod

        script_sentences = re_mod.split(r"[।\n.!?]+", response)
        script_sentences = [s.strip() for s in script_sentences if s.strip() and len(s.strip()) > 10]

        if len(script_sentences) > 12:
            step = len(script_sentences) // 10
            combined = []
            for k in range(0, len(script_sentences), max(step, 1)):
                group = " ".join(script_sentences[k : k + max(step, 1)])
                combined.append(group)
            script_sentences = combined[:12]

        print(f"[DOCUMENTARY] Script split into {len(script_sentences)} sentence groups")

        video_keyword_data = generate_video_search_keywords(script_sentences)
        print(f"[DOCUMENTARY] Got {len(video_keyword_data)} video search keyword sets")

        num_keywords = len(video_keyword_data)

        # Distribute keywords proportionally across audio duration
        # Each keyword group gets an equal share of audio time
        search_terms = []
        for idx in range(num_keywords):
            t_start = (idx * total_duration) / num_keywords
            t_end = ((idx + 1) * total_duration) / num_keywords
            keywords = video_keyword_data[idx].get("keywords", ["cinematic documentary scene"])
            search_terms.append([[t_start, t_end], keywords])

        print(f"[DOCUMENTARY] Created {len(search_terms)} segments aligned to script sections")
    elif mode == "viral" and viral_data:
        print("[VIRAL] Mapping AI-generated visual prompts to timed blocks...")
        scenes = viral_data.get("scenes", [])
        num_scenes = len(scenes) if scenes else 1

        # Calculate word counts per scene to proportionally allocate time
        scene_word_counts = []
        for s in scenes:
            vo = s.get("voiceover", "")
            scene_word_counts.append(max(len(vo.split()), 1))
        total_words = sum(scene_word_counts)

        search_terms = []
        t_cursor = 0.0
        for i, s in enumerate(scenes):
            proportion = scene_word_counts[i] / total_words
            t_end = t_cursor + (proportion * total_duration)
            if i == len(scenes) - 1:
                t_end = total_duration  # Ensure last scene covers to end
            search_terms.append([[t_cursor, t_end], [s.get("visual_prompt", "viral cinematic scene")]])
            t_cursor = t_end
        print(f"[VIRAL] Created {len(search_terms)} scene-based visual prompts (word-proportional)")
    else:
        search_terms = getVideoSearchQueriesTimed(response, timed_captions)

    # 6. Fetch Media
    if search_terms is not None:
        background_video_urls = await generate_video_url(
            search_terms, VIDEO_SERVER, orientation_landscape=orientation_landscape
        )
    else:
        background_video_urls = None

    background_video_urls = merge_empty_intervals(background_video_urls)

    # 7. Composite Final Output
    if background_video_urls is None:
        raise RuntimeError("No background videos/images generated.")

    video_file_path = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)

    # Cleanup request-specific audio file
    try:
        os.remove(SAMPLE_FILE_NAME)
    except Exception:
        pass

    return {
        "video_file_path": video_file_path,
        "script_used": response,
        "final_language": language,
        "video_server": VIDEO_SERVER,
    }


@app.post("/generate")
async def generate_video(
    input_text: str = Form(...),
    mode: str = Form("script"), # 'script', 'topic', or 'documentary'
    duration: int = Form(60),   # 30, 60, 120, 180
    language: str = Form("marathi"),
    use_ai_images: bool = Form(False),
    use_stock_images: bool = Form(False)
):
    try:
        result = await _generate_video_core(
            input_text=input_text,
            mode=mode,
            duration=duration,
            language=language,
            use_ai_images=use_ai_images,
            use_stock_images=use_stock_images,
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


# ── NEW: Documentary Script Generator ──────────────────────────────────────────
@app.post("/generate-documentary-script")
async def generate_documentary_script(
    topic: str = Form(...),
    duration: int = Form(120),
):
    """Generate a suspenseful Hindi documentary script for the given topic."""
    try:
        script = generate_script(
            topic=f"{topic}",
            duration=duration,
            mode="documentary",
        )
        return JSONResponse({"status": "success", "script": script})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── NEW: Visual Prompt Generator ───────────────────────────────────────────────
@app.post("/generate-visual-prompts")
async def generate_visual_prompts_endpoint(
    script: str = Form(...),
):
    """
    Accept a script (multiple lines separated by newline or \\n literal).
    Return one detailed documentary-style visual prompt per line.
    """
    try:
        # Support both real newlines and escaped \n from form data
        lines = script.replace("\\n", "\n").split("\n")
        lines = [l for l in lines if l.strip()]
        if not lines:
            return JSONResponse({"status": "error", "message": "No script lines provided"}, status_code=400)
        prompts = generate_visual_prompts(lines)
        return JSONResponse({"status": "success", "prompts": prompts})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/viral-ideas")
async def get_viral_ideas(niche: str = "mystery"):
    """Fetch viral topic ideas for a niche."""
    try:
        from utility.script.viral_engine import generate_viral_topics
        topics = generate_viral_topics(niche, count=5)
        return {"status": "success", "topics": topics}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── NEW: Viral Shorts Script Generator ────────────────────────────────────────
@app.post("/generate-viral-script")
async def generate_viral_script_endpoint(
    topic: str = Form(...),
    duration: int = Form(60),
    language: str = Form("english"),
):
    """
    Generate a fully structured viral Shorts script (JSON with title, hook,
    scenes, loop_ending, hashtags) WITHOUT producing a video.
    Use this to preview/copy the script before running the full pipeline.
    """
    try:
        data = await asyncio.to_thread(
            generate_viral_short, topic, duration, language
        )
        voiceover = extract_voiceover_script(data)
        return JSONResponse({
            "status":    "success",
            "title":     data.get("title", ""),
            "hook":      data.get("hook", ""),
            "scenes":    data.get("scenes", []),
            "loop_ending": data.get("loop_ending", ""),
            "hashtags":  data.get("hashtags", []),
            "voiceover_script": voiceover,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
