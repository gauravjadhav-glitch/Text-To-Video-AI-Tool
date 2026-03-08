import json
from utility.config import get_config


def clean_markdown(text):
    """Remove markdown formatting from text to prevent TTS issues."""
    import re
    
    # 1. Remove triple code blocks first
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # 2. Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # 3. Remove bold formatting (**text**)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # 4. Remove italic formatting (*text*) - Skip underscores to avoid breaking words like C++_lib
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    
    # 5. Remove headers (# text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # 6. Remove links [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # 7. Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def generate_script(topic, duration=60, mode='shorts'):
    """Generate a script.
    mode options: 'shorts', 'documentary', 'viral_story', 'facts', 'comparison'
    """
    config = get_config()
    client = config.get_llm_client()
    model = config.get_llm_model()
    provider = config.get_llm_provider()

    word_count = 70 if duration == 30 else 140

    if mode == 'documentary':
        prompt = _build_documentary_prompt(duration)
    elif mode == 'viral_story':
        prompt = _build_shorts_prompt(duration, word_count, style="Viral Storytelling / Mystery")
    elif mode == 'comparison':
        prompt = _build_shorts_prompt(duration, word_count, style="Funny Comparison (Expectation vs Reality)")
    elif mode == 'facts':
        prompt = _build_shorts_prompt(duration, word_count, style="Mind-blowing Facts")
    else: # Default shorts
        prompt = _build_shorts_prompt(duration, word_count)

    if provider == 'gemini':
        content = _call_gemini_with_retry(client, topic, prompt)
    else:
        content = _call_openai_with_retry(client, model, topic, prompt)

    return _parse_script_response(content)


def _build_shorts_prompt(duration, word_count, style="viral content"):
    return (
        f"""You are a seasoned content writer for a YouTube Shorts channel, specializing in {style}. 
        Your shorts are concise, lasting exactly {duration} seconds.
        
        CRITICAL INSTRUCTIONS:
        - Write EXACTLY about {word_count} words. 
        - Do NOT exceed {word_count + 10} words.
        - Ensure every second is engaging and has a hook.

        Important instructions:
        - All content must be relevant to the specific topic or style requested (e.g., if asked for a comparison, follow that style).
        - If the topic is related to a specific country (e.g., India), ensure the facts, cultural context, and tone reflect that accurately.
        - Do not use random or unrelated information.
        - If the script mentions a location, person, or event, it should be described in a way that allows for matching visuals.
        - Maintain consistency with the story and ensure it is highly interesting and unique.

        For instance, if the user asks for 'Weird facts about India':
        You would produce content like this:
        - The world's highest cricket ground is in Chail, Himachal Pradesh, built in 1893.
        - India was the first country to mine diamonds.
        - The village of Shani Shignapur has no doors or locks on any houses.

        Strictly output the script in a JSON format like below, and only provide a parsable JSON object with the key 'script'.

        # Output
        {{"script": "Here is the script ..."}}
        """
    )


def _build_documentary_prompt(duration):
    return (
        f"""Aap ek professional Hindi documentary scriptwriter hain jo highly suspenseful aur gripping content likhte hain.
        Aapko ek {duration} second ki documentary script likhni hai in Hindi mein.

        Script ke avashyak hisse (MANDATORY STRUCTURE):
        1. HOOK (5-8 seconds): Ek aisa powerful opening line jo viewer ko immediately rok de — ek shocking fact, ek burning sawaal, ya ek dramatic statement se shuru karo. Creator guidance mat likho.
        2. SCENES (80%): Multiple cinematic scenes jo story ko aage badhate hain. Har scene suspense aur curiosity banaye rakhe. Short, punchy sentences use karo.
        3. CLOSING LINE (last 5 seconds): Ek strong, memorable conclusion line jo viewer ke dimaag mein ghus jaye.

        Zaruri niyam:
        - Pure script ko SIRF Hindi mein likho
        - Koi creator guidance nahi likhni (jaise: 'yahan cut karo', 'background mein yeh dikhao', etc.)
        - Script directly bolne wali honi chahiye jaise koi narrator bol raha ho
        - Suspense aur emotional tension throughout banaye rakho
        - Strong hooks use karo jo viewer ko last tak roke
        - Write EXACTLY {duration * 2.3:.0f} words in Hindi.
        - Do NOT exceed {duration * 2.5:.0f} words.

        Sirf JSON format mein output do, koi extra text nahi:
        {{"script": "Yahan script likho..."}}
        """
    )


def _parse_script_response(content):
    """Parse LLM response and extract clean script text."""
    try:
        text = content
        for prefix in ['content:', 'content =', 'content: ', 'content=']:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        json_start = text.find('{')
        json_end = text.rfind('}')

        if json_start == -1 or json_end == -1:
            raise ValueError("No valid JSON found in response")

        script_text = text[json_start:json_end+1]
        data = json.loads(script_text, strict=False)
        
        if "script" not in data:
             raise ValueError("Missing 'script' key in JSON response")
             
        script = clean_markdown(data["script"])
        return script
    except Exception as e:
        print(f"Error parsing script response: {e}")
        raise


def _call_openai_with_retry(client, model, topic, prompt, retries=3):
    import time
    for i in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": topic}
                ],
                timeout=30
            )
            return response.choices[0].message.content
        except Exception as e:
            if i == retries - 1:
                raise RuntimeError(f"OpenAI/Groq request failed after {retries} attempts: {e}")
            print(f"LLM attempt {i+1} failed, retrying... ({e})")
            time.sleep(2)


def _call_gemini_with_retry(client, topic, prompt, retries=3):
    import time
    for i in range(retries):
        try:
            response = client.generate_content(
                contents=[
                    {"role": "user", "parts": [{"text": f"{prompt}\n\nTopic: {topic}"}]}
                ],
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "max_output_tokens": 8192,
                }
            )
            text = response.text or ""
            
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            return text.strip()
        except Exception as e:
            if i == retries - 1:
                raise RuntimeError(f"Gemini request failed after {retries} attempts: {e}")
            print(f"Gemini attempt {i+1} failed, retrying... ({e})")
            time.sleep(2)
