import os 
import requests
from utility.utils import log_response,LOG_TYPE_PEXEL
from utility.config import get_config


def search_photos(query_string, orientation_landscape=True):
    config = get_config()
    pexels_api_key = config.get_pexels_api_key()

    url = "https://api.pexels.com/v1/search"
    headers = {
        "Authorization": pexels_api_key,
        "User-Agent": "Mozilla/5.0"
    }
    params = {
        "query": query_string,
        "orientation": "landscape" if orientation_landscape else "portrait",
        "per_page": 1
    }

    response = requests.get(url, headers=headers, params=params)
    return response.json()

def getBestPhoto(query_string, orientation_landscape=True):
    query_string = _clean_query(query_string)
    data = search_photos(query_string, orientation_landscape)
    if 'photos' in data and data['photos']:
        # Extract the highest resolution link
        # For portrait we want large2x or original
        photo = data['photos'][0]
        if orientation_landscape:
            return photo['src']['landscape']
        else:
            return photo['src']['portrait']
    return None

def search_videos(query_string, orientation_landscape=True):
    config = get_config()
    pexels_api_key = config.get_pexels_api_key()

    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": pexels_api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {
        "query": query_string,
        "orientation": "landscape" if orientation_landscape else "portrait",
        "per_page": 15
    }

    response = requests.get(url, headers=headers, params=params)
    json_data = response.json()
    log_response(LOG_TYPE_PEXEL,query_string,response.json())

    # Check for API errors
    if response.status_code != 200:
        error_msg = json_data.get('error', f'HTTP {response.status_code}')
        raise Exception(f"Pexels API error: {error_msg}. Please check your PEXELS_API_KEY in .env file.")

    if 'videos' not in json_data:
        raise Exception("Pexels API returned unexpected response (no 'videos' field). Please check your PEXELS_API_KEY in .env file.")

    return json_data

def _clean_query(query_string, max_words=8):
    """Truncate query to max_words simple English words for Pexels API compatibility."""
    import re
    # Strip non-alphanumeric chars (keep spaces)
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', query_string)
    words = clean.split()[:max_words]
    return " ".join(words).strip() or "cinematic video"

def getBestVideo(query_string, orientation_landscape=True, used_vids=None):
    if used_vids is None:
        used_vids = []
    query_string = _clean_query(query_string)
    try:
        vids = search_videos(query_string, orientation_landscape)
    except Exception as e:
        print(f"Pexels video search failed for '{query_string}': {e}")
        return None
    videos = vids.get('videos', [])

    # Filter and extract videos based on orientation
    if orientation_landscape:
        filtered_videos = [video for video in videos if video['width'] > video['height']]
    else:
        filtered_videos = [video for video in videos if video['height'] > video['width']]

    # If no results match orientation, just use the original list
    if not filtered_videos:
        filtered_videos = videos

    # Sort the filtered videos by duration, preferring videos around 10-15 seconds
    sorted_videos = sorted(filtered_videos, key=lambda x: abs(15-int(x['duration'])))

    # Extract the video URLs
    for video in sorted_videos:
        # Pexels provides multiple files, try to find a good one
        best_file = None
        for video_file in video['video_files']:
            # Prefer HD/Full HD but accept anything
            if orientation_landscape:
                if video_file['width'] >= 1280 and video_file['height'] >= 720:
                    best_file = video_file['link']
                    break
            else:
                if video_file['height'] >= 1280 and video_file['width'] >= 720:
                    best_file = video_file['link']
                    break
        
        # If no preferred file found, just take the first one
        if not best_file and video['video_files']:
            best_file = video['video_files'][0]['link']
            
        if best_file and not (best_file.split('.hd')[0] in used_vids):
            return best_file

    print("NO LINKS found for this round of search with query :", query_string)
    return None


async def generate_video_url(timed_video_searches, video_server, orientation_landscape=True):
    timed_video_urls = []
    if video_server == "pexel":
        used_links = []
        for (t1, t2), search_terms in timed_video_searches:
            url = ""
            for query in search_terms:
                url = getBestVideo(query, orientation_landscape=orientation_landscape, used_vids=used_links)
                if url:
                    used_links.append(url.split('.hd')[0])
                    break
            timed_video_urls.append([[t1, t2], url])
    elif video_server == "stable_diffusion":
        from utility.video.image_generator import get_images_for_video
        timed_video_urls = await get_images_for_video(timed_video_searches, orientation_landscape=orientation_landscape)
    elif video_server == "pexels_image":
        for (t1, t2), search_terms in timed_video_searches:
            url = ""
            for query in search_terms:
                url = getBestPhoto(query, orientation_landscape=orientation_landscape)
                if url:
                    break
            timed_video_urls.append([[t1, t2], url])

    return timed_video_urls
