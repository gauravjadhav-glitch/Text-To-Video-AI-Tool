import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import requests
from utility.config import get_config

def generate_image_url_sync(prompt, size="1024x1792"):
    """
    Synchronous image generation helper for ThreadPool.
    """
    config = get_config()
    client = config.get_openai_client()
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        print(f"Error generating image with DALL-E: {e}")
        return None

async def generate_image_url(prompt, size="1024x1792"):
    # Using asyncio.to_thread is more lightweight and uses the default executor
    return await asyncio.to_thread(generate_image_url_sync, prompt, size)

async def get_images_for_video(timed_video_searches, orientation_landscape=False):
    """
    Generate a list of [[t1, t2], image_url] for each segment in parallel.
    """
    size = "1792x1024" if orientation_landscape else "1024x1792"
    
    tasks = []
    for (t1, t2), search_terms in timed_video_searches:
        search_term = search_terms[0] if search_terms else "interesting historical visual"
        
        # Sanitize prompt
        forbidden_terms = ['invader', 'muslim', 'muslims', 'war', 'killing', 'blood', 'death', 'execution']
        for term in forbidden_terms:
            search_term = search_term.lower().replace(term, "historical event")
            
        # If the prompt is already detailed (e.g., from documentary visual prompt generator),
        # use it directly. Otherwise, wrap with standard cinematic template.
        if len(search_term) > 100:
            # Already a detailed documentary-style prompt — use as-is
            prompt = search_term
        else:
            # Refined prompt for realism and YouTube Shorts appeal
            prompt = (
                f"A hyper-realistic, high-detail cinematic photograph of {search_term}. "
                f"Style: National Geographic 8k photography, authentic cultural details, "
                f"cinematic lighting, natural real-world textures, capturing a candid historical moment. "
                f"No text, no watermarks, professional focus, real people, real places."
            )
        
        tasks.append(generate_image_url(prompt, size=size))
    
    urls = await asyncio.gather(*tasks)
    
    timed_image_urls = []
    for i, ((t1, t2), _) in enumerate(timed_video_searches):
        timed_image_urls.append([[t1, t2], urls[i]])
        
    return timed_image_urls
