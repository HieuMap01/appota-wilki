"""List available Gemini models for this API key."""
import sys
sys.path.insert(0, 'src')
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)
models = client.models.list()
for m in models:
    # Only show generative models
    if hasattr(m, 'name'):
        name = m.name if isinstance(m.name, str) else str(m.name)
        if 'flash' in name.lower() or 'pro' in name.lower() or 'gemini' in name.lower():
            print(name)
