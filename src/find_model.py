"""Quick test: try multiple models and pick first that responds."""
import sys
sys.path.insert(0, 'src')
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

CANDIDATES = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
]

prompt = "Xin chao. Hay tra loi ngan gon bang tieng Viet: 1+1 bang may?"

for model in CANDIDATES:
    try:
        print(f"Testing {model}...", flush=True)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50,
            ),
        )
        print(f"  -> OK: {response.text.strip()[:100]}")
        break
    except Exception as e:
        print(f"  -> FAIL: {str(e)[:120]}")
