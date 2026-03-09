import json
import time
from utility.config import get_config

def _call_llm_with_retry(client, provider, model, prompt, user_input, retries=3):
    """Internal helper for LLM calls with retry logic."""
    for i in range(retries):
        try:
            if provider == 'gemini':
                response = client.generate_content(
                    contents=[{"role": "user", "parts": [{"text": f"{prompt}\n\nInput: {user_input}"}]}],
                    generation_config={"temperature": 0.8, "top_p": 0.9}
                )
                text = response.text or ""
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input}
                    ],
                    timeout=30
                )
                text = response.choices[0].message.content
            
            # Clean JSON markdown if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            
            return json.loads(text.strip(), strict=False)
        except Exception as e:
            if i == retries - 1:
                raise RuntimeError(f"Viral Engine LLM call failed: {e}")
            time.sleep(2)

def generate_viral_topics(niche="mystery", count=10):
    """1. Viral Topic Generator: Automatically generates trending video ideas."""
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    prompt = f"""
    Generate {count} viral YouTube Shorts / Documentary topic ideas in the '{niche}' niche.
    
    CRITICAL INSTRUCTIONS (INDIA FIRST):
    - MANDATORY: Every single topic MUST be related to INDIA (Indian people, places, history, culture, or current events).
    - TARGET AUDIENCE: Indian viewers on YouTube/Instagram.
    - RECENT TRENDS: Focus on what is currently trending or traditionally 'viral' in India (e.g., specific myths, local news, cricket legends, bollywood secrets, political twists).
    - HOOK STRATEGY: Use curiosity gaps that work specifically for the Indian audience ("Bharat ka sabse bada rahasya...", "Why Indians are doing X...").

    Rules for Virality:
    - High curiosity & click-worthy hooks.
    - Shocking, mysterious, or extremely relatable.
    - Visual-heavy concepts that are easy to illustrate with AI images.

    Output ONLY a JSON object:
    {{"topics": ["Short clickable title: Brief description", ...]}}
    """
    
    return _call_llm_with_retry(client, provider, model, prompt, niche)["topics"]

def generate_hooks(topic, count=5):
    """2. Hook Optimizer: Generates high-retention openings for any topic."""
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    prompt = f"""
    Write {count} viral YouTube Shorts hooks for the topic: '{topic}'
    
    Hook Strategy:
    - Must stop the scroll in the first 2 seconds.
    - Use curiosity gaps ("You won't believe...", "The secret about...").
    - Keep it under 15 words.
    - Force the user to keep watching for the 'Answer'.

    Output ONLY a JSON object:
    {{"hooks": ["Hook Line 1", "Hook Line 2", ...]}}
    """
    
    return _call_llm_with_retry(client, provider, model, prompt, topic)["hooks"]

def generate_storyboard(topic, duration=60):
    """3. Scene Mapper: Converts a script into scenes with visual prompts."""
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    prompt = f"""
    Create a detailed storyboard for a {duration} second video on: '{topic}'
    
    Structure:
    - Split the narrative into scenes (approx 5-8 seconds each).
    - For each scene, provide the 'narration' (text to be spoken) and a 'visual_prompt' (for AI image/video generation).
    - Visual prompts should be extremely descriptive (e.g., 'abandoned ship in green fog, cinematic overhead shot, 8k').

    Output ONLY a JSON object:
    {{
      "theme": "Video Theme",
      "scenes": [
        {{
          "narration": "Narration text here",
          "visual_prompt": "Cinematic visual description for AI"
        }},
        ...
      ]
    }}
    """
    
    return _call_llm_with_retry(client, provider, model, prompt, topic)
