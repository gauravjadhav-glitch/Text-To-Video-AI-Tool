from utility.config import get_config


async def generate_audio(text, outputFilename, voice=None):
    config = get_config()
    tts_provider = config.get_tts_provider()
    if voice is None:
        voice = config.get_tts_voice()
    
    if tts_provider == 'edgetts':
        from utility.tts.edgetts_tts import generate_audio as edgetts_audio
        await edgetts_audio(text, outputFilename, voice)
    elif tts_provider == 'openai':
        from utility.tts.openai_tts import generate_audio as openai_audio
        await openai_audio(text, outputFilename, voice)
    elif tts_provider == 'elevenlabs':
        from utility.tts.elevenlabs_tts import generate_audio as elevenlabs_audio
        await elevenlabs_audio(text, outputFilename, voice)
    else:
        raise ValueError(f"Unknown TTS provider: {tts_provider}")
