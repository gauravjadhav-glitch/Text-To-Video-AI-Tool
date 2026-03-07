import time
import os
import tempfile
import zipfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, ImageClip,
                              TextClip, VideoFileClip, ColorClip)
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
import requests
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from utility.config import get_config

def download_file(url, filename):
    with open(filename, 'wb') as f:
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        f.write(response.content)

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server):
    config = get_config()
    OUTPUT_FILE_NAME = "rendered_video.mp4"
    magick_path = get_program_path("magick")
    print(magick_path)
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'
    
    audio_file_clip = AudioFileClip(audio_file_path)
    duration = audio_file_clip.duration
    
    # 1. Determine base size
    is_landscape = config.get_video_orientation()
    base_size = (1920, 1080) if is_landscape else (1080, 1920)
    
    # 2. Start with a black background to prevent blank spots
    background_clip = ColorClip(size=base_size, color=(0, 0, 0)).set_duration(duration)
    visual_clips = [background_clip]
    
    downloaded_files = []
    for (t1, t2), url in background_video_data:
        if not url:
            print(f"Skipping segment {t1}-{t2} because URL is None")
            continue
            
        # Download file
        is_image = video_server in ["stable_diffusion", "pexels_image"]
        filename = tempfile.NamedTemporaryFile(delete=False, suffix=".png" if is_image else ".mp4").name
        try:
            download_file(url, filename)
            downloaded_files.append(filename)
            
            if is_image:
                # Create ImageClip
                clip = ImageClip(filename)
                clip = clip.set_start(t1)
                clip = clip.set_end(t2)
                clip = clip.set_duration(t2-t1)
                
                # Resize to cover screen nicely
                if is_landscape:
                    clip = clip.resize(height=1080)
                    if clip.w < 1920:
                        clip = clip.resize(width=1920)
                else:
                    clip = clip.resize(width=1080)
                    if clip.h < 1920:
                        clip = clip.resize(height=1920)
                
                # Add a subtle zoom effect (Ken Burns)
                # Zoom from 1.0 to 1.1 over the duration
                clip = clip.resize(lambda t: 1.0 + 0.1 * (t / clip.duration))
                
                # Center the clip
                clip = clip.set_position("center")
                visual_clips.append(clip)
            else:
                # Create VideoFileClip
                video_clip = VideoFileClip(filename)
                
                # Avoid out of bounds if Pexels video is shorter than segment
                clip_duration = t2 - t1
                if video_clip.duration < clip_duration:
                    video_clip = video_clip.loop(duration=clip_duration)
                
                video_clip = video_clip.set_start(t1)
                video_clip = video_clip.set_end(t2)
                
                # Resize to fill frame
                if is_landscape:
                    video_clip = video_clip.resize(height=1080)
                    if video_clip.w < 1920:
                        video_clip = video_clip.resize(width=1920)
                else:
                    video_clip = video_clip.resize(width=1080)
                    if video_clip.h < 1920:
                        video_clip = video_clip.resize(height=1920)
                
                video_clip = video_clip.set_position("center")
                visual_clips.append(video_clip)
        except Exception as e:
            print(f"Error processing segment {t1}-{t2}: {e}")
    
    audio_clips = []
    audio_file_clip = AudioFileClip(audio_file_path)
    audio_clips.append(audio_file_clip)
    
    # Only add captions if enabled in config
    if config.get_captions_enabled():
        for (t1, t2), text in timed_captions:
            # Get caption styling from config
            font_size = config.get_caption_font_size()
            font_color = config.get_caption_font_color()
            stroke_width = config.get_caption_stroke_width()
            stroke_color = config.get_caption_stroke_color()
            font_face = config.get_caption_font_face()
            caption_position = config.get_caption_position()

            # Convert caption position string to MoviePy format
            # For 1080p video: top=100, center=540, bottom=1000
            if caption_position == 'bottom_center':
                position = ["center", 1000]
            elif caption_position == 'bottom_left':
                position = ["left", 1000]
            elif caption_position == 'bottom_right':
                position = ["right", 1000]
            elif caption_position == 'top':
                position = ["center", 100]
            elif caption_position == 'center':
                position = ["center", 540]
            else: # Default to bottom_center
                position = ["center", 1000]

            text_clip = TextClip(txt=text, font=font_face, fontsize=font_size, color=font_color, stroke_width=stroke_width, stroke_color=stroke_color, method="label")
            text_clip = text_clip.set_start(t1)
            text_clip = text_clip.set_end(t2)
            text_clip = text_clip.set_position(position)
            visual_clips.append(text_clip)
    
    video = CompositeVideoClip(visual_clips)
    
    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')
    
    # Clean up downloaded files
    for filename in downloaded_files:
        try:
            os.remove(filename)
        except:
            pass

    return OUTPUT_FILE_NAME
