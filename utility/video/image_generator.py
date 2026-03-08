import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import requests
from utility.config import get_config
import re

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
        original_term = search_terms[0] if search_terms else "historical scene"
        
        # Highly aggressive sanitation for DALL-E safety policy
        search_term = original_term
        # Remove explicitly violent words that trigger filters
        unsafe_patterns = [
            r'\bmassacre\b', r'\bkillings?\b', r'\bbloody?\b', r'\bdeath\b', r'\bdead\b',
            r'\bexecution\b', r'\bmurder\b', r'\battack\b', r'\bviolence\b', r'\bcorpse\b',
            r'\bslaughter\b', r'\bgore\b', r'\btorture\b', r'\bvictim\b', r'\bshooting\b'
        ]
        for pattern in unsafe_patterns:
            search_term = re.sub(pattern, "historical event", search_term, flags=re.IGNORECASE)
            
        # If the prompt is already detailed (e.g., from documentary visual prompt generator),
        # use it directly. Otherwise, wrap with standard cinematic template.
        if len(search_term) > 100:
            prompt = search_term
        else:
            prompt = (
                f"A hyper-realistic, high-detail cinematic photograph of {search_term}. "
                f"Style: National Geographic 8k photography, authentic cultural details, "
                f"cinematic lighting, natural real-world textures, capturing a candid historical moment. "
                f"No text, no watermarks, professional focus, real people, real places."
            )
        
        tasks.append(generate_image_url(prompt, size=size))
    
    urls = await asyncio.gather(*tasks)
    
    # Fallback to Pexels if DALL-E fails
    timed_image_urls = []
    for i, ((t1, t2), search_terms) in enumerate(timed_video_searches):
        url = urls[i]
        
        if not url:
            # DALL-E failed. Try a simple Pexels fallback with narrowed query.
            print(f"[IMAGE GEN] DALL-E failed for segment {t1}-{t2}. Trying Pexels fallback...")
            query = search_terms[0] if search_terms else "history"
            
            # Clean query for Pexels (take first 4-5 words and remove safety risks)
            safe_query = " ".join(query.split()[:5])
            safe_query = re.sub(r'massacre|killing|blood|death|dead|execution|murder', 'historical', safe_query, flags=re.IGNORECASE)
            
            from utility.video.background_video_generator import getBestPhoto
            url = getBestPhoto(safe_query, orientation_landscape=orientation_landscape)
            
            if not url:
                # Last resort: generic documentary background
                url = "https://images.pexels.com/photos/3761509/pexels-photo-3761509.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
        
        timed_image_urls.append([[t1, t2], url])
        
    return timed_image_urls
