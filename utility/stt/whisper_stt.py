import whisper_timestamped as whisper
from whisper_timestamped import load_model, transcribe_timestamped
import re


def generate_timed_captions(audio_filename, model_size="base", language="mr", task="transcribe"):
    WHISPER_MODEL = load_model(model_size)
    
    gen = transcribe_timestamped(WHISPER_MODEL, audio_filename, language=language, task=task, verbose=False, fp16=False)
    
    return getCaptionsWithTime(gen)


def splitWordsBySize(words, maxCaptionSize):
    
    halfCaptionSize = maxCaptionSize / 2
    captions = []
    while words:
        caption = words[0]
        words = words[1:]
        while words and len(caption + ' ' + words[0]) <= maxCaptionSize:
            caption += ' ' + words[0]
            words = words[1:]
            if len(caption) >= halfCaptionSize and words:
                break
        captions.append(caption)
    return captions


def getTimestampMapping(whisper_analysis):
    index = 0
    locationToTimestamp = {}
    text = whisper_analysis['text']
    
    for segment in whisper_analysis['segments']:
        for word in segment['words']:
            clean_text = cleanWord(word['text'])
            newIndex = index + len(clean_text)+1
            locationToTimestamp[(index, newIndex)] = (word['start'], word['end'])
            index = newIndex
    return locationToTimestamp


def cleanWord(word):
    
    return re.sub(r'[^\w\s\-_%\'\u0080-\uFFFF]', '', word)


def interpolateTimeFromDict(word_position, d):
    
    for key, value in d.items():
        if key[0] <= word_position <= key[1]:
            return value
    return None


def getCaptionsWithTime(whisper_analysis, maxCaptionSize=15, considerPunctuation=False):

    CaptionsPairs = []
    last_end = 0

    # First pass: collect all valid word timings
    raw_words = []
    for segment in whisper_analysis['segments']:
        for word_info in segment['words']:
            clean_word = cleanWord(word_info['text'])
            if clean_word:
                raw_words.append((word_info['start'], word_info['end'], clean_word))

    if not raw_words:
        return CaptionsPairs

    # Calculate average word duration for realistic fallback
    valid_durations = [end - start for start, end, _ in raw_words if end > start]
    avg_word_dur = sum(valid_durations) / len(valid_durations) if valid_durations else 0.3
    # Clamp to reasonable range
    avg_word_dur = max(0.1, min(avg_word_dur, 1.0))

    for start, end, clean_word in raw_words:
        # Fix timestamp issues using average word duration instead of fixed 0.3s
        if start >= end or start < last_end or end <= last_end:
            start = last_end
            end = last_end + avg_word_dur

        last_end = end
        CaptionsPairs.append(((start, end), clean_word))

    return CaptionsPairs
