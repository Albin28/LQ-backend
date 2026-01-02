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

# --- PUBLIC ROUTES ---

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

# --- NEW ROUTE: MP DASHBOARD ---
@app.route('/mps')
def mps_dashboard():
    # Fetch all MP records from Firebase
    mps_ref = db.collection('mps')
    docs = mps_ref.stream()
    
    mps_list = []
    for doc in docs:
        data = doc.to_dict()
        mps_list.append(data)
        
    return render_template('mps.html', mps=mps_list)

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

# 3. LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- ADMIN ROUTES (SECURE) ---

# 4. ADMIN DASHBOARD (View & Manage)
@app.route('/admin')
def admin_dashboard():
    # Security Check: Kick user out if not logged in
    if 'user' not in session:
        return redirect(url_for('login'))

    # Fetch all bills
    bills_ref = db.collection('bills')
    docs = bills_ref.stream()
    
    bills_list = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id # We need the ID to delete/edit
        bills_list.append(data)
        
    return render_template('admin.html', bills=bills_list)

# 5. DELETE BILL LOGIC
@app.route('/delete_bill/<bill_id>', methods=['POST'])
def delete_bill(bill_id):
    # Security Check
    if 'user' not in session:
        return "Unauthorized", 401

    try:
        db.collection('bills').document(bill_id).delete()
        return "Deleted", 200
    except Exception as e:
        return str(e), 500

# 6. UPDATE STATUS LOGIC
@app.route('/update_status/<bill_id>/<new_status>', methods=['POST'])
def update_status(bill_id, new_status):
    # Security Check
    if 'user' not in session:
        return "Unauthorized", 401

    try:
        db.collection('bills').document(bill_id).update({
            'status': new_status
        })
        return "Updated", 200
    except Exception as e:
        return str(e), 500

# --- HELPER API ---
@app.route('/api/bills')
def get_bills_json():
    docs = db.collection('bills').stream()
    return jsonify([doc.to_dict() for doc in docs])

if __name__ == '__main__':
    app.run(debug=True, port=5000)