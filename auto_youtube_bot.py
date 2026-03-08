import asyncio
import os
import json
import random
from utility.script.script_generator import generate_script
from utility.script.viral_engine import generate_viral_topics, generate_hooks, generate_storyboard
from utility.video.background_video_generator import generate_video_url # or image gen
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.render.render_engine import get_output_media
from utility.video.youtube_uploader import upload_video
from utility.config import get_config

async def run_auto_bot(niche="mystery", duration=60):
    """
    🔥 COMPLETE AI YOUTUBE BOT 🔥
    1. Find viral topics
    2. Pick the best hook
    3. Generate cinematic storyboard (narration + visuals)
    4. Render final video
    5. (Optional) Auto-upload to YouTube
    """
    print(f"🚀 Starting Auto Bot for niche: {niche}...")

    # 1. Generate Viral Topics
    print("Searching for trending ideas...")
    topics = generate_viral_topics(niche, count=5)
    best_topic = random.choice(topics)
    print(f"✅ Selected Topic: {best_topic}")

    # 2. Optimize Hook
    print("Crafting viral hook...")
    hooks = generate_hooks(best_topic, count=3)
    best_hook = hooks[0]
    print(f"✅ Hook: {best_hook}")

    # 3. Generate Storyboard (Scenes)
    print("Creating cinematic storyboard...")
    storyboard = generate_storyboard(f"{best_hook}. {best_topic}", duration)
    full_narration = " ".join([s["narration"] for s in storyboard["scenes"]])
    print(f"✅ Narration Preview: {full_narration[:100]}...")

    # 4. Generate Audio (Voiceover)
    print("Generating AI voiceover...")
    audio_path = "auto_voice.wav"
    await generate_audio(full_narration, audio_path)

    # 5. Generate Timed Captions
    print("Transcribing with Whisper...")
    timed_captions = generate_timed_captions(audio_path)

    # 6. Fetch Background Visuals (Using Storyboard prompts)
    # Mapping storyboard visuals to Pexels/AI scenes (simplified demo version)
    # In a full bot, we'd call generate_video_url for each visual_prompt
    print("Simulating visual gathering (Scene -> AI Prompts)...")
    # For this demo, let's use the standard search pipeline to fill the gaps
    from utility.video.video_search_query_generator import getVideoSearchQueriesTimed
    search_terms = getVideoSearchQueriesTimed(full_narration, timed_captions)
    
    # Simple fallback structure if LLM fails
    if search_terms is None:
        search_terms = [[[0.0, float(duration)], [best_topic]]]

    background_video_urls = await generate_video_url(search_terms, "pexels_image")

    # 7. Final Render
    print("🎬 Rendering Final Video...")
    output_video = f"{best_topic.replace(' ', '_')[:30]}.mp4"
    rendered_path = get_output_media(audio_path, timed_captions, background_video_urls, "pexels_image")
    
    # Rename to our descriptive topic name
    if os.path.exists(rendered_path):
        os.rename(rendered_path, output_video)
        print(f"⭐️ DONE! Video ready at: {output_video}")

    # 8. (Optional) Upload to YouTube
    # Only if client_secrets.json exists
    if os.path.exists("client_secrets.json"):
        print(f"📤 Uploading '{output_video}' to YouTube...")
        title = f"{best_hook} #Shorts #{niche.replace(' ', '')}"
        desc = f"Mind-blowing facts about {best_topic}. Don't forget to subscribe!"
        tags = [niche, "mystery", "science", "facts", "shorts"]
        
        try:
            upload_video(output_video, title, desc, tags)
            print("✅ Upload Completed!")
        except Exception as e:
            print(f"❌ Upload failed: {e}")
    else:
        print("💡 Skip upload (client_secrets.json not found).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", default="mystery", help="Niche for topics")
    parser.add_argument("--duration", type=int, default=60, help="Video duration in seconds")
    
    args = parser.parse_args()
    asyncio.run(run_auto_bot(args.niche, args.duration))
