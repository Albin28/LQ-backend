import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = "legisq_secure_random_key_2025"  # Needed for Login session

# --- FIREBASE SETUP ---
def get_firebase_credentials():
    # 1. Look for file locally (Laptop)
    if os.path.exists("serviceAccountKey.json"):
        return "serviceAccountKey.json"
    # 2. Look for file on Cloud (Render)
    elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
        return "/etc/secrets/serviceAccountKey.json"
    else:
        return None

if not firebase_admin._apps:
    key_path = get_firebase_credentials()
    if key_path:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    else:
        print("❌ WARNING: No Firebase Key found! Database will not work.")

db = firestore.client()

# --- ROUTES ---

# 1. HOME PAGE (The Main Dashboard)
@app.route('/')
def home():
    # Fetch real bills from Firebase
    bills_ref = db.collection('bills')
    docs = bills_ref.stream()

    bills_list = []
    for doc in docs:
        data = doc.to_dict()
        # Ensure every bill has these fields to prevent crashes
        bill_data = {
            'title': data.get('title', 'Untitled'),
            'status': data.get('status', 'Unknown'),
            'category': data.get('category', 'General'),
            'date_introduced': data.get('date_introduced', 'N/A'),
            'summary': data.get('summary', 'No summary available.'),
            'file_path': data.get('file_path', '') # Critical for Download Button
        }
        bills_list.append(bill_data)

    # Render the new UI (index.html)
    return render_template('index.html', bills=bills_list)

# 2. LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Hardcoded Admin Check
        if username == "admin" and password == "admin123":
            session['user'] = "admin"
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Username or Password!")
            return redirect(url_for('login'))
            
    return render_template('login.html')

# 3. ADMIN DASHBOARD
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    return """
    <h1>Welcome Admin!</h1>
    <p>Secure area to Add/Edit Bills (Coming Soon).</p>
    <a href='/'>Back to Dashboard</a> | <a href='/logout'>Logout</a>
    """

# 4. LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- HELPER API (Optional, kept for testing) ---
@app.route('/api/bills')
def get_bills_json():
    docs = db.collection('bills').stream()
    return jsonify([doc.to_dict() for doc in docs])

if __name__ == '__main__':
    app.run(debug=True, port=5000)