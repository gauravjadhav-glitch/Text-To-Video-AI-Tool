from dotenv import load_dotenv
import os
load_dotenv()
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:10] if os.getenv('OPENAI_API_KEY') else 'None'}")
print(f"GROQ_API_KEY: {os.getenv('GROQ_API_KEY')[:10] if os.getenv('GROQ_API_KEY') else 'None'}")
print(f"PEXELS_API_KEY: {os.getenv('PEXELS_API_KEY')[:10] if os.getenv('PEXELS_API_KEY') else 'None'}")
