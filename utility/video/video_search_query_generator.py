import json
import re
from utility.config import get_config
from utility.utils import log_response, LOG_TYPE_GPT

prompt = """# Instructions
Given the following video script and timed captions, extract exactly THREE visually concrete keywords/segments for every 5-8 seconds of video.

IMPORTANT RULES:
1. Each visual segment MUST be at least 3.0 seconds long. NEVER create segments like [[1.0, 1.2]].
2. The FIRST segment MUST start at 0.0 seconds.
3. The LAST segment MUST end at EXACTLY the end time provided (the total video duration).
4. Every segment time (t1, t2) must be strictly consecutive with NO gaps — t2 of one segment equals t1 of the next.
5. Segments must cover the ENTIRE video from 0.0 to the end time. Do NOT stop early.
6. Keywords must be in ENGLISH and visually concrete (e.g., 'cat sleeping' NOT 'emotional moment').
7. If the script is about a funny comparison (Expectation vs Reality), ensure the segments align with the transition keywords.

Output ONLY a JSON array: [[[t1, t2], ["keyword1", "keyword2", "keyword3"]], ...]. No extra text.
"""

def fix_json(json_str):
    # Replace typographical apostrophes with straight quotes
    json_str = json_str.replace("’", "'")
    # Replace any incorrect quotes (e.g., mixed single and double quotes)
    json_str = json_str.replace("“", "\"").replace("”", "\"").replace("‘", "\"").replace("’", "\"")
    # Add escaping for quotes within the strings
    json_str = json_str.replace('"you didn"t"', '"you didn\'t"')
    return json_str

def getVideoSearchQueriesTimed(script,captions_timed):
    end = captions_timed[-1][0][1]
    max_retries = 3
    retry_count = 0

    try:
        out = [[[0,0],""]]
        while True:
            if retry_count >= max_retries:
                print(f"Max retries ({max_retries}) reached. Using current result or fallback.")
                if out == [[[0,0],""]]:
                    return None
                break

            content = call_OpenAI(script,captions_timed)
            try:
                out = json.loads(content, strict=False)
            except Exception as e:
                print("JSON parse error, attempting to fix...")
                print(e)
                try:
                    content = fix_json(content.replace("```json", "").replace("```", ""))
                    out = json.loads(content, strict=False)
                except Exception as e2:
                    print(f"Failed to fix JSON: {e2}")
                    retry_count += 1
                    continue

            if not out or not isinstance(out, list) or len(out) == 0:
                retry_count += 1
                continue

            # Accept if last segment ends within 3 seconds of actual end
            last_end = out[-1][0][1]
            if abs(last_end - end) <= 3.0 or last_end >= end * 0.8:
                break
            else:
                print(f"[SEARCH] Segments end at {last_end:.1f}s but audio ends at {end:.1f}s, retrying...")
                retry_count += 1
                continue

        # Fix the timeline: ensure first segment starts at 0 and last ends at actual end
        if out and out != [[[0,0],""]]:
            out[0][0][0] = 0.0
            out[-1][0][1] = end

            # Merge segments shorter than 3s
            merged = []
            curr = out[0]
            for i in range(1, len(out)):
                if (curr[0][1] - curr[0][0]) < 3.0:
                    curr[0][1] = out[i][0][1]
                    if isinstance(curr[1], list) and isinstance(out[i][1], list):
                        curr[1] = list(dict.fromkeys(curr[1] + out[i][1]))[:3]
                else:
                    merged.append(curr)
                    curr = out[i]
            merged.append(curr)
            return merged

        return out
    except Exception as e:
        print("error in response",e)

    return None

def call_OpenAI(script,captions_timed):
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()
    
    end_time = captions_timed[-1][0][1] if captions_timed else 30.0
    user_content = """Script: {}
Total Video Duration: {:.1f} seconds (segments MUST cover from 0.0 to {:.1f})
Timed Captions:{}
""".format(script, end_time, end_time, "".join(map(str,captions_timed)))
    print("Content", user_content)
    
    if provider == 'gemini':
        response = client.generate_content(
            contents=[
                {"role": "user", "parts": [{"text": f"{prompt}\n\n{user_content}"}]}
            ],
            generation_config={
                "temperature":1.0,
                "top_p": 0.9,
                "max_output_tokens": 8192,
            }
        )
        text = response.text.strip()
    else:
        response = client.chat.completions.create(
            model=model,
            temperature=1,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ]
        )
        text = response.choices[0].message.content.strip()
    
    text = re.sub(r'\s+', ' ', text)
    
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    # Remove "content:" prefix if present (Gemini sometimes adds this)
    if text.startswith('content:'):
        text = text[9:].strip()
    
    # Also check for "content =" format
    if text.startswith('content ='):
        text = text[9:].strip()
    
    # Remove markdown code blocks if still present
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        parsed = json.loads(text)
        print("Text", text)
        log_response(LOG_TYPE_GPT,script,text)
        return text
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Original text: {text[:200]}")
        
        # Try to find complete JSON by looking for patterns
        try:
            # Find last complete array or object
            last_bracket = text.rfind(']')
            if last_bracket > 0:
                trimmed = text[:last_bracket+1]
                parsed = json.loads(trimmed)
                print(f"Successfully trimmed JSON to {len(trimmed)} chars")
                log_response(LOG_TYPE_GPT,script,trimmed)
                return trimmed
        except Exception as e2:
            print(f"Trim attempt failed: {e2}")
        
        # Last resort: default fallback structure
        print("Using default fallback structure")
        default_json = '[[[0.16, 5.29], ["default background video", "stock footage", "generic scene"]], [[5.29, 10.29], ["stock video", "background footage", "video content"]]]'
        return default_json

def merge_empty_intervals(segments):
    """
    Ensure every segment has a URL by borrowing from neighbors.
    Also ensures NO timeline gaps exist (100% video coverage).
    """
    if not segments:
        print("No background segments to merge")
        return None
    
    # Sort by start time just in case
    segments.sort(key=lambda x: x[0][0])
    
    # 1. Timeline Gap Filling & sanitization
    sanitized = []
    for i, (interval, url) in enumerate(segments):
        t1, t2 = interval
        
        # If there's a gap between the end of the last segment and the start of this one
        if i > 0:
            prev_t2 = sanitized[-1][0][1]
            if t1 > prev_t2:
                # Fill the gap by extending the previous segment's end time
                sanitized[-1][0][1] = t1
            elif t1 < prev_t2:
                # Fix overlap
                t1 = prev_t2
        
        # Ensure the first segment starts at 0.0
        if i == 0 and t1 > 0:
            t1 = 0.0
            
        # Ensure t2 > t1
        if t2 <= t1:
            t2 = t1 + 1.0
            
        sanitized.append([[t1, t2], url])
    
    # 2. Forward Fill: Replace None with the previous valid URL
    last_valid_url = None
    for i in range(len(sanitized)):
        if sanitized[i][1]:
            last_valid_url = sanitized[i][1]
        elif last_valid_url:
            sanitized[i][1] = last_valid_url
            
    # 3. Backward Fill: In case the first few are None, fill from the first valid one
    first_valid_url = None
    for j in range(len(sanitized)-1, -1, -1):
        if sanitized[j][1]:
            first_valid_url = sanitized[j][1]
        elif first_valid_url:
            sanitized[j][1] = first_valid_url

    # 4. Global Fallback (Last Resort)
    if not any(s[1] for s in sanitized):
        print("CRITICAL: No valid URLs found in any segment. Using fallback placeholder.")
        placeholder = "https://images.pexels.com/photos/301920/pexels-photo-301920.jpeg"
        for k in range(len(sanitized)):
            sanitized[k][1] = placeholder

    # 5. Merge consecutive identical URLs
    merged = []
    if sanitized:
        curr = sanitized[0]
        for m in range(1, len(sanitized)):
            if sanitized[m][1] == curr[1]:
                curr[0][1] = sanitized[m][0][1]
            else:
                merged.append(curr)
                curr = sanitized[m]
        merged.append(curr)
        
    return merged
