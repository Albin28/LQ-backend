import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from google import genai

# Load API Key from .env file
load_dotenv()

app = Flask(__name__)

# --- 1. NEW: SECURITY KEY (Required for Login/Sessions) ---
app.secret_key = "legisq_secure_random_key_2025" 

# --- SMART CONFIGURATION (Preserved) ---
def get_firebase_credentials():
    # Option 1: Look for file on Laptop (Root folder)
    if os.path.exists("serviceAccountKey.json"):
        return "serviceAccountKey.json"
    
    # Option 2: Look for file on Render (Secret folder)
    elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
        return "/etc/secrets/serviceAccountKey.json"
    
    else:
        print("❌ CRITICAL: No Service Account Key found!")
        return None

# Initialize Firebase
if not firebase_admin._apps:
    key_path = get_firebase_credentials()
    if key_path:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    else:
        # This will show up in Render logs if it fails
        raise FileNotFoundError("Could not find serviceAccountKey.json in root or /etc/secrets/")

db = firestore.client()

# 2. AI Setup (The New 2025 SDK) (Preserved)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- ROUTES ---

# 1. HOME PAGE (Preserved your mps.html)
@app.route('/')
def home():
    # This loads your existing page with the AI features
    return render_template('mps.html')

# 2. LOGIN PAGE (New)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Hardcoded Check (Matches your Android App)
        if username == "admin" and password == "admin123":
            session['user'] = "admin" # Save login state
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Username or Password!")
            return redirect(url_for('login'))
            
    # We need to make sure you created 'templates/login.html' from the previous step!
    return render_template('login.html')

# 3. ADMIN DASHBOARD (New)
@app.route('/admin')
def admin_dashboard():
    # Security Check: Kick them out if not logged in
    if 'user' not in session:
        return redirect(url_for('login'))
        
    return """
    <h1>Welcome Admin!</h1>
    <p>This is the secure area to Add/Edit Bills.</p>
    <a href='/'>Go to Public Home</a> | <a href='/logout'>Logout</a>
    """

# 4. LOGOUT (New)
@app.route('/logout')
def logout():
    session.pop('user', None) # Clear login state
    return redirect(url_for('home'))

# --- API ENDPOINTS (Preserved) ---

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
            model="gemini-2.0-flash", 
            contents=f"Summarize this legislative bill in 3 simple bullet points:\n\n{bill_text}"
        )
        
        print("✅ AI Responded!") # DEBUG PRINT
        return jsonify({"summary": response.text})

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}") # PRINTS THE REAL ERROR TO TERMINAL
        return jsonify({"summary": f"System Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)