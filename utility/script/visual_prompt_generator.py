import json
import re
from utility.config import get_config


VISUAL_PROMPT_SYSTEM = """You are an expert AI visual director specializing in cinematic documentary films.

The user will provide a documentary script with multiple lines (numbered).
Your task: For EACH numbered line, generate ONE highly detailed, documentary-style visual/image generation prompt.

IMPORTANT RULES:
1. Every prompt must share the SAME consistent visual style: "cinematic documentary photography, dramatic golden-hour or desaturated color grade, shallow depth of field, film grain, high contrast, photorealistic, 8K".
2. Every prompt must fit the SAME emotional theme: dark, historical, grave, suspenseful — as seen in BBC/Netflix documentary films.
3. VERY IMPORTANT: DALL-E strictly blocks any descriptions of violence, blood, gore, weapons, dead bodies, or real-world massacres. YOU MUST avoid these concepts entirely! Instead, use symbolic and safe representations (e.g., "an abandoned historical courtyard with long shadows", "somber atmosphere with dust glowing in sunbeams", "empty streets", "discarded historical belongings"). Ensure every prompt passes strict safety filters.
4. Each prompt must be in ENGLISH, highly descriptive, and visual (no abstract concepts).
5. Do NOT include any creator notes, narration, or scene direction — only visual descriptions.
6. Each prompt should be 2-4 sentences long.
6. Output ONLY a JSON array like this:
[
  {"line": 1, "prompt": "..."},
  {"line": 2, "prompt": "..."},
  ...
]
No extra text outside of the JSON array.
"""


VIDEO_SEARCH_SYSTEM = """You are a video search expert. The user will provide documentary script lines (numbered, possibly in Hindi or other languages).

For EACH line, generate 2-3 SHORT English search keywords that would find the BEST matching stock video footage on Pexels/Shutterstock.

CRITICAL RULES:
1. Keywords must be in ENGLISH only (translate Hindi/Marathi if needed).
2. Keywords must be visually concrete and specific (e.g., "Krishna temple Vrindavan", "Indian flute player sunset", "ancient Indian palace aerial").
3. Each keyword should be 2-4 words max — simple search queries, NOT long descriptions.
4. Keywords must DIRECTLY match what the narration is talking about — if the line mentions a river, search for river footage; if it mentions a battle, search for ancient warriors.
5. Prefer cinematic, dramatic footage terms: add words like "cinematic", "aerial", "slow motion", "dramatic" when appropriate.
6. Output ONLY a JSON array:
[
  {"line": 1, "keywords": ["keyword1", "keyword2"]},
  {"line": 2, "keywords": ["keyword1", "keyword2"]},
  ...
]
No extra text outside the JSON array.
"""


def generate_video_search_keywords(script_lines: list[str]) -> list[dict]:
    """
    Given script lines (Hindi/English), return Pexels-friendly English search keywords.
    Returns: [{"line": 1, "keywords": ["keyword1", "keyword2"]}, ...]
    """
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    numbered = "\n".join(
        f"{i+1}. {line.strip()}" for i, line in enumerate(script_lines) if line.strip()
    )

    user_content = f"Documentary script lines:\n{numbered}"

    if provider == "gemini":
        response = client.generate_content(
            contents=[{"role": "user", "parts": [{"text": f"{VIDEO_SEARCH_SYSTEM}\n\n{user_content}"}]}],
            generation_config={"temperature": 0.7, "top_p": 0.85, "max_output_tokens": 4096},
        )
        raw = _strip_code_fences(response.text.strip())
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VIDEO_SEARCH_SYSTEM},
                {"role": "user", "content": user_content},
            ],
        )
        raw = _strip_code_fences(response.choices[0].message.content.strip())

    parsed = _parse_response(raw)

    result = []
    valid_lines = [l for l in script_lines if l.strip()]
    for i, line in enumerate(valid_lines):
        entry = {"line": i + 1, "original": line.strip(), "keywords": []}
        for p in parsed:
            if p.get("line") == i + 1:
                entry["keywords"] = p.get("keywords", [])
                break
        if not entry["keywords"]:
            entry["keywords"] = ["cinematic documentary scene"]
        result.append(entry)

    return result


def generate_visual_prompts(script_lines: list[str]) -> list[dict]:
    """
    Given a list of script lines, return a list of dicts:
    [{"line": 1, "original": "...", "prompt": "..."}, ...]
    """
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    numbered = "\n".join(
        f"{i+1}. {line.strip()}" for i, line in enumerate(script_lines) if line.strip()
    )

    user_content = f"Documentary script lines:\n{numbered}"

    if provider == "gemini":
        raw = _call_gemini(client, user_content)
    else:
        raw = _call_openai_groq(client, model, user_content)

    prompts = _parse_response(raw)

    # Merge original lines back in
    result = []
    valid_lines = [l for l in script_lines if l.strip()]
    for i, line in enumerate(valid_lines):
        entry = {"line": i + 1, "original": line.strip(), "prompt": ""}
        for p in prompts:
            if p.get("line") == i + 1:
                entry["prompt"] = p.get("prompt", "")
                break
        result.append(entry)

    return result


def _call_gemini(client, user_content: str) -> str:
    response = client.generate_content(
        contents=[
            {"role": "user", "parts": [{"text": f"{VISUAL_PROMPT_SYSTEM}\n\n{user_content}"}]}
        ],
        generation_config={
            "temperature": 0.7,
            "top_p": 0.85,
            "max_output_tokens": 8192,
        },
    )
    text = response.text.strip()
    return _strip_code_fences(text)


def _call_openai_groq(client, model: str, user_content: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VISUAL_PROMPT_SYSTEM},
            {"role": "user", "content": user_content},
        ],
    )
    text = response.choices[0].message.content.strip()
    return _strip_code_fences(text)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _parse_response(raw: str) -> list[dict]:
    """Parse LLM response into list of {line, prompt} dicts."""
    try:
        # Find JSON array boundaries
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("No JSON array found in response")
        data = json.loads(raw[start : end + 1], strict=False)
        return data
    except Exception as e:
        print(f"[VisualPromptGenerator] JSON parse error: {e}")
        print(f"[VisualPromptGenerator] Raw response snippet: {raw[:300]}")
        return []
