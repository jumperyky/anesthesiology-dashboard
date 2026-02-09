import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

print("Fetching available models...")
try:
    # List models
    # Note: google-genai SDK usage for listing models
    # Client.models.list() returns an iterator
    pager = client.models.list()
    
    print(f"{'Model Name':<30} | {'Display Name'}")
    print("-" * 50)
    
    found = False
    for model in pager:
        # Filter for generateContent supported models
        if "generateContent" in model.supported_actions:
            name = model.name.replace("models/", "")
            print(f"{name:<30} | {model.display_name}")
            found = True
            
    if not found:
        print("No models found that support generateContent.")

except Exception as e:
    print(f"Error fetching models: {e}")
