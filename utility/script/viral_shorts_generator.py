import json
import re
from utility.config import get_config


# ─────────────────────────────────────────────────────────────────────────────
#  PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_viral_prompt(topic: str, duration: int, language: str) -> str:
    """Build the viral Shorts prompt for the given language."""

    lang_instructions = {
        "marathi": "Write ALL voiceover text in Marathi (Devanagari script).",
        "hindi":   "Write ALL voiceover text in Hindi (Devanagari script).",
        "english": "Write ALL voiceover text in English.",
    }
    lang_note = lang_instructions.get(language.lower(), lang_instructions["english"])

    # For 30s videos: exactly 4 scenes to match the 4-scene storyboard format
    if duration <= 30:
        scene_count = 4
    elif duration <= 60:
        scene_count = max(3, duration // 15)
    else:
        scene_count = max(4, duration // 20)

    return f"""You are an elite viral YouTube Shorts scriptwriter whose videos routinely
hit 10M+ views. Your writing style: fast-paced, emotionally charged, curiosity-driven.

TOPIC: {topic}
DURATION: {duration} seconds
LANGUAGE NOTE: {lang_note}

YOUR GOAL: Maximise viewer retention using the Hook → Hold → Payoff framework.
- Hook  : First 3 seconds — shocking fact, provocative question, or dramatic statement.
- Hold  : Middle scenes — escalating tension, curiosity gaps, short punchy sentences.
- Payoff: Loop ending — a revelation or twist that makes viewers rewatch.

SCENE COUNT: Produce EXACTLY {scene_count} scenes.

VISUAL PROMPT RULES (very important for video search):
- visual_prompt must be SHORT (5-8 words max), in plain English only.
- It must be a concrete, searchable phrase for stock video libraries like Pexels.
- Examples of GOOD visual_prompt: "Indian festival celebration crowd", "rangoli decoration colorful floor", "family prayer temple morning", "dhol drums street festival India"
- Examples of BAD visual_prompt: "A cinematic wide-angle shot of an emotional sunset scene" — too abstract, not searchable.
- Also provide keyword_hints: an array of 3 alternative search terms (simple English) for fallback.

CULTURAL ACCURACY:
- If the topic is an Indian festival (Gudi Padwa, Diwali, Holi, etc.), use accurate cultural visuals.
- Reference specific cultural elements: rangoli, diyas, traditional clothing (nauvari saree, kurta), temples, dhol, marigold garlands, etc.

STRICT RULES:
1. Every voiceover sentence must be ≤15 words.
2. Every visual_prompt must be ≤8 words, plain English, Pexels-searchable.
3. Every caption must be ≤6 words (shown on-screen overlay).
4. hashtags: 6-10 relevant tags (include #shorts).
5. Return ONLY valid JSON — no markdown, no extra text.

JSON FORMAT:
{{
  "title": "<clickable YouTube title, ≤60 chars>",
  "hook": "<first 3-second spoken line>",
  "scenes": [
    {{
      "scene": 1,
      "voiceover": "<what the narrator says>",
      "visual_prompt": "<5-8 word Pexels search phrase>",
      "keyword_hints": ["<alt search 1>", "<alt search 2>", "<alt search 3>"],
      "caption": "<short on-screen text overlay>"
    }}
  ],
  "loop_ending": "<final line that creates a loop / makes viewer rewatch>",
  "hashtags": ["#shorts", "..."]
}}
"""




# ─────────────────────────────────────────────────────────────────────────────
#  CORE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_viral_short(topic: str, duration: int = 60, language: str = "english") -> dict:
    """
    Generate a fully structured viral Shorts script.

    Returns a dict with keys:
        title, hook, scenes, loop_ending, hashtags
    Each scene has: scene, voiceover, visual_prompt, caption
    """
    config   = get_config()
    client   = config.get_llm_client()
    model    = config.get_llm_model()
    provider = config.get_llm_provider()

    prompt = _build_viral_prompt(topic, duration, language)

    raw = _call_llm(client, model, provider, topic, prompt)
    data = _parse_viral_response(raw)
    return data


def extract_voiceover_script(viral_data: dict) -> str:
    """
    Flatten the structured viral data into a single plain-text voiceover script
    suitable for TTS generation.

    Order: hook → scene voiceovers → loop_ending
    """
    parts = []

    hook = viral_data.get("hook", "").strip()
    if hook:
        parts.append(hook)

    for scene in viral_data.get("scenes", []):
        vo = scene.get("voiceover", "").strip()
        if vo:
            parts.append(vo)

    ending = viral_data.get("loop_ending", "").strip()
    if ending:
        parts.append(ending)

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
#  LLM CALLERS
# ─────────────────────────────────────────────────────────────────────────────

def _call_llm(client, model, provider, topic, prompt, retries=3):
    import time
    for attempt in range(retries):
        try:
            if provider == "gemini":
                return _call_gemini(client, topic, prompt)
            else:
                return _call_openai(client, model, topic, prompt)
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"LLM call failed after {retries} attempts: {e}")
            print(f"[viral_shorts] attempt {attempt+1} failed, retrying… ({e})")
            time.sleep(2)


def _call_openai(client, model, topic, prompt):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user",   "content": topic},
        ],
        timeout=45,
    )
    return response.choices[0].message.content


def _call_gemini(client, topic, prompt):
    response = client.generate_content(
        contents=[{"role": "user", "parts": [{"text": f"{prompt}\n\nTopic: {topic}"}]}],
        generation_config={"temperature": 0.85, "top_p": 0.9, "max_output_tokens": 8192},
    )
    text = response.text or ""
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _parse_viral_response(content: str) -> dict:
    """Extract and validate the viral JSON from the LLM response."""
    text = content.strip()

    # Strip any markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$",          "", text)

    # Find the outermost JSON object
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No valid JSON object found in LLM response. Raw: {content[:300]}")

    data = json.loads(text[start : end + 1], strict=False)

    # Validate required keys
    required = {"title", "hook", "scenes", "loop_ending", "hashtags"}
    missing  = required - data.keys()
    if missing:
        raise ValueError(f"Viral script JSON missing keys: {missing}")

    if not isinstance(data["scenes"], list) or len(data["scenes"]) == 0:
        raise ValueError("Viral script must contain at least one scene.")

    return data
