import os
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from utility.script.script_generator import generate_script
from utility.script.visual_prompt_generator import generate_visual_prompts
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
    "english": "en"
}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

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
        SAMPLE_FILE_NAME = "audio_tts_web.wav"
        
        # Documentary mode always uses AI images
        is_documentary = (mode == "documentary")
        
        if is_documentary or use_ai_images:
            VIDEO_SERVER = "stable_diffusion"
        elif use_stock_images:
            VIDEO_SERVER = "pexels_image"
        else:
            VIDEO_SERVER = "pexel"
        
        # Check if we should use OpenAI TTS for premium voices
        if language.lower() in ["english-premium", "english-pro"]:
            tts_provider_override = "openai"
        else:
            tts_provider_override = None
        
        config = get_config()
        orientation_landscape = config.get_video_orientation()
        
        input_text = input_text.strip()
        if not input_text:
            return JSONResponse({"status": "error", "message": "Input cannot be empty"}, status_code=400)

        # 1. Generate Script
        if is_documentary:
            # Documentary mode: auto-generate Hindi documentary script
            print(f"[DOCUMENTARY] Generating script for: {input_text} ({duration}s)")
            response = generate_script(
                topic=input_text,
                duration=duration,
                mode="documentary"
            )
            print(f"[DOCUMENTARY] Script generated: {response[:100]}...")
            # Force language to Hindi for documentary
            language = "hindi"
        elif mode == "topic":
            response = generate_script(f"Write a {duration} second script in {language} about: {input_text}", duration=duration)
        else:
            response = input_text

        # 2. Get correct voice and STT language
        voice = VOICE_MAP.get(language.lower(), "mr-IN-AarohiNeural")
        stt_lang = STT_LANG_MAP.get(language.lower(), "mr")

        # 3. Generate Audio
        if tts_provider_override:
            # Temporarily override provider for this request
            import os
            original_provider = os.getenv("TTS_PROVIDER")
            os.environ["TTS_PROVIDER"] = tts_provider_override
            try:
                await generate_audio(response, SAMPLE_FILE_NAME, voice=voice)
            finally:
                if original_provider:
                    os.environ["TTS_PROVIDER"] = original_provider
        else:
            await generate_audio(response, SAMPLE_FILE_NAME, voice=voice)

        # 4. Extract Timed Captions (passing the correct language to Whisper)
        # Note: we need to update timed_captions_generator to receive language
        from utility.stt.whisper_stt import generate_timed_captions as whisper_stt
        if is_documentary:
            timed_captions = whisper_stt(SAMPLE_FILE_NAME, model_size="tiny", language=stt_lang, task="translate")
        else:
            timed_captions = whisper_stt(SAMPLE_FILE_NAME, model_size="tiny", language=stt_lang)

        # 5. Create Search Queries / Visual Prompts Map
        if is_documentary:
            # Documentary: generate cinematic visual prompts for each script line
            print("[DOCUMENTARY] Generating visual prompts from script...")
            import re as re_mod
            # Split script into sentences (Hindi uses । as sentence delimiter, also split on newlines)
            script_sentences = re_mod.split(r'[।\n]+', response)
            script_sentences = [s.strip() for s in script_sentences if s.strip() and len(s.strip()) > 10]
            
            # OPTIMIZATION: Limit to max ~10 sentences to avoid too many LLM + DALL-E calls
            if len(script_sentences) > 12:
                # Combine consecutive sentences to get ~10-12 groups
                step = len(script_sentences) // 10
                combined = []
                for k in range(0, len(script_sentences), max(step, 1)):
                    group = " ".join(script_sentences[k:k+max(step,1)])
                    combined.append(group)
                script_sentences = combined[:12]
            
            print(f"[DOCUMENTARY] Script split into {len(script_sentences)} sentence groups")
            
            visual_prompt_data = generate_visual_prompts(script_sentences)
            
            print(f"[DOCUMENTARY] Got {len(visual_prompt_data)} visual prompts")
            
            # OPTIMIZATION: Instead of mapping to every tiny caption segment,
            # divide total audio duration into fixed ~10-second blocks.
            # Each block gets one visual prompt → one DALL-E image.
            # This limits calls to ~6 for 60s, ~12 for 120s, ~18 for 180s.
            
            total_duration = max(tc[0][1] if isinstance(tc[0], (list, tuple)) else tc[0] for tc in timed_captions)
            BLOCK_SECONDS = 10.0  # one image per 10 seconds
            num_blocks = max(1, int(total_duration / BLOCK_SECONDS))
            num_prompts = len(visual_prompt_data)
            
            search_terms = []
            for b in range(num_blocks):
                t_start = b * BLOCK_SECONDS
                t_end = min((b + 1) * BLOCK_SECONDS, total_duration)
                # Pick the visual prompt proportionally
                prompt_idx = min(int(b * num_prompts / num_blocks), num_prompts - 1)
                prompt_text = visual_prompt_data[prompt_idx].get("prompt", "cinematic documentary scene")
                search_terms.append([[t_start, t_end], [prompt_text]])
            
            print(f"[DOCUMENTARY] Created {len(search_terms)} segments (~{BLOCK_SECONDS}s each) for DALL-E")
        else:
            search_terms = getVideoSearchQueriesTimed(response, timed_captions)

        # 6. Fetch Media
        if search_terms is not None:
            # THIS IS NOW ASYNC!
            background_video_urls = await generate_video_url(search_terms, VIDEO_SERVER, orientation_landscape=orientation_landscape)
        else:
            background_video_urls = None

        background_video_urls = merge_empty_intervals(background_video_urls)

        # 7. Composite Final Output
        if background_video_urls is not None:
            video_file_path = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            return JSONResponse({
                "status": "success", 
                "video_url": f"/download/{video_file_path}", 
                "script_used": response
            })
        else:
            return JSONResponse({"status": "error", "message": "No background videos/images generated.", "video_url": None})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/download/{file_name}")
async def download_video(file_name: str):
    if os.path.exists(file_name):
        return FileResponse(file_name, media_type="video/mp4", filename=file_name)
    return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)


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
