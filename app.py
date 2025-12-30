import os
from flask import Flask, jsonify, render_template, request
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from google import genai

# Load API Key from .env file
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
# 1. Firebase Setup
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. AI Setup (The New 2025 SDK)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('mps.html')

@app.route('/api/mps')
def get_mps():
    docs = db.collection('mps').stream()
    return jsonify([doc.to_dict() for doc in docs])

@app.route('/api/bills')
def get_bills():
    docs = db.collection('bills').stream()
    return jsonify([doc.to_dict() for doc in docs])

@app.route('/api/summarize', methods=['POST'])
def summarize_bill():
    print("--- 🧠 AI Request Received ---") # DEBUG PRINT
    try:
        data = request.json
        bill_text = data.get('text', '')
        
        print(f"📄 Text Length: {len(bill_text)} chars") # DEBUG PRINT

        if not bill_text:
            return jsonify({"summary": "Error: No text found to summarize."})

        # Call AI
        print("⏳ Calling Google Gemini...") # DEBUG PRINT
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"Summarize this legislative bill in 3 simple bullet points:\n\n{bill_text}"
        )
        
        print("✅ AI Responded!") # DEBUG PRINT
        return jsonify({"summary": response.text})

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}") # PRINTS THE REAL ERROR TO TERMINAL
        return jsonify({"summary": f"System Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)