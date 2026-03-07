import os
from utility.config import get_config

async def generate_audio(text, outputFilename, voice="coral"):
    """
    Generate audio using OpenAI's gpt-4o-mini-tts model (OpenAI.fm)
    """
    config = get_config()
    client = config.get_openai_client()
    
    # Map from our config names to OpenAI voices if needed
    # Defaulting to 'coral' as suggested by openai.fm
    
    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice.lower(), # OpenAI.fm voices: alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse
            input=text,
            response_format="mp3"
        )
        response.stream_to_file(outputFilename)
    except Exception as e:
        print(f"Error generating audio with OpenAI TTS: {e}")
        raise
