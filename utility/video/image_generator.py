import asyncio
import re
import urllib.parse

async def get_images_for_video(timed_video_searches, orientation_landscape=False):
    """
    Generate a list of [[t1, t2], image_url] for each segment using Pexels Photos (Reliable & Free).
    """
    from utility.video.background_video_generator import getBestPhoto
    timed_image_urls = []
    
    for (t1, t2), search_terms in timed_video_searches:
        # Take the most important keywords from the visual description
        prompt = search_terms[0] if search_terms else "cinematic"
        
        # Extract the core subject from the prompt to avoid over-specific search failure
        # Basically use first 5-8 words or words that look like keywords
        clean_prompt = " ".join(prompt.split()[:8])
        clean_prompt = re.sub(r'[^a-zA-Z0-9\s]', '', clean_prompt)
        
        # Fallback search if the long prompt fails
        url = getBestPhoto(clean_prompt, orientation_landscape=orientation_landscape)
        
        if not url:
            # Try an even simpler search
            simple_prompt = " ".join(clean_prompt.split()[:3])
            url = getBestPhoto(simple_prompt, orientation_landscape=orientation_landscape)
            
        if not url:
            # Last resort generic cinematic photo
            url = "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg"
            
        timed_image_urls.append([[t1, t2], url])
        
    return timed_image_urls
