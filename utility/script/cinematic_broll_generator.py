import json
import re
from utility.config import get_config

def generate_cinematic_broll_script(user_input: str, duration: int = 30) -> dict:
    """
    Transforms a simple user input into a highly technical Director's Vision script.
    Focuses entirely on visual cues (lighting, camera movement, style) without voiceover.
    """
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    scene_count = max(2, duration // 10) # 10 seconds per scene
    
    system_instruction = f"""You are a Professional Cinematographer and AI Prompt Engineer. Your job is to transform simple user descriptions into structured, technical scripts for an AI video generation model.

Rules for Transformation:
1. Do not add voiceover or dialogue.
2. Focus on visual cues: Camera angles (Close-up, Wide, Tracking), Lighting (Golden hour, Neon, Volumetric), and Texture.
3. Format: Output a structured JSON script that describes the visual progression clearly.
4. Length: Ensure the visual density is sufficient for a {duration}-second video.
5. Create exactly {scene_count} distinct scenes.
6. Provide short Pexels-searchable keyword_hints as fallbacks.

Output Format (JSON strictly):
{{
    "title": "A short descriptive title",
    "total_duration": {duration},
    "scenes": [
        {{
             "scene_id": 1,
             "duration": 10,
             "visual_prompt": "Wide establishing shot of a Neo-Tokyo inspired cityscape at night. Heavy torrential rain with realistic water droplets hitting the camera lens. Volumetric neon signs in pink and cyan reflecting off wet pavement.",
             "keyword_hints": ["futuristic city night", "neon rain city", "cyberpunk street"]
        }}
    ]
}}
"""
    
    # Provider calling
    if provider == "gemini":
        response = client.generate_content(
            contents=[{
                "role": "user", 
                "parts": [{"text": f"{system_instruction}\n\nUser Input: {user_input}"}]
            }],
            generation_config={"temperature": 0.8, "top_p": 0.9}
        )
        text = response.text or ""
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ]
        )
        text = response.choices[0].message.content or ""
        
    # Clean JSON
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    
    start = text.find("{")
    end = text.rfind("}")
    
    if start == -1 or end == -1:
         raise ValueError(f"No valid JSON object found in internal transformer response. Raw: {text[:300]}")
         
    return json.loads(text[start : end + 1], strict=False)
