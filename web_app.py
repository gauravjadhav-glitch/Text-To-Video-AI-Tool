import os
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from utility.config import get_config

app = FastAPI()

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
    mode: str = Form("script"), # 'script' or 'topic'
    duration: int = Form(60),   # 30 or 60
    language: str = Form("marathi"),
    use_ai_images: bool = Form(False),
    use_stock_images: bool = Form(False)
):
    try:
        SAMPLE_FILE_NAME = "audio_tts_web.wav"
        if use_ai_images:
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

        # 1. Generate Script if in topic mode
        if mode == "topic":
            # Pass topic and duration to generator
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
        timed_captions = whisper_stt(SAMPLE_FILE_NAME, language=stt_lang)

        # 5. Create Search Queries Map
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
