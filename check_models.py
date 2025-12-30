import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: API Key not found in .env file")
else:
    client = genai.Client(api_key=api_key)
    print(f"--- 🔍 Scanning for available models for key: {api_key[:5]}... ---")
    
    try:
        # This asks Google: "What can I use?"
        for model in client.models.list():
            if "generateContent" in model.supported_actions:
                print(f"✅ Available: {model.name}")
                
    except Exception as e:
        print(f"❌ Error scanning: {e}")