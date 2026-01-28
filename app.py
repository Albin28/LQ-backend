import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURATION ---
from dotenv import load_dotenv
load_dotenv() # Load .env file

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "legisq_default_dev_key") 

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

# 1. HOME PAGE (Bills Dashboard)
@app.route('/')
def home():
    # Fetch real bills from Firebase
    bills_ref = db.collection('bills')
    # Limit to 50 newest bills to save reads
docs = bills_ref.order_by('date_introduced', direction=firestore.Query.DESCENDING).limit(50).stream()

    bills_list = []
    for doc in docs:
        data = doc.to_dict()
        bill_data = {
            'title': data.get('title', 'Untitled'),
            'status': data.get('status', 'Unknown'),
            'category': data.get('category', 'General'),
            'date_introduced': str(data.get('date_introduced', 'N/A'))[:10],
            'summary': data.get('summary', ''),
            'file_path': data.get('file_path', '') 
        }
        bills_list.append(bill_data)

    return render_template('index.html', bills=bills_list)

# 2. MP DASHBOARD (Public View)
@app.route('/mps')
def mps_dashboard():
    # Fetch all MP records
    mps_ref = db.collection('mps')
    docs = mps_ref.stream()
    
    mps_list = []
    for doc in docs:
        data = doc.to_dict()
        mps_list.append(data)
        
    return render_template('mps.html', mps=mps_list)

# 3. CURRENT AFFAIRS PAGE (NEW!)
@app.route('/current_affairs')
def current_affairs():
    # Fetch all CA records
    ca_ref = db.collection('current_affairs')
    docs = ca_ref.stream()
    
    ca_list = []
    for doc in docs:
        data = doc.to_dict()
        ca_list.append(data)
    
    # Sort by Date (Newest First) - assumes YYYY-MM-DD format
    ca_list.sort(key=lambda x: x.get('date', ''), reverse=True)
        
    return render_template('current_affairs.html', news=ca_list)

# 3. LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Secure Admin Check (Environment Variables)
        valid_user = os.getenv("ADMIN_USERNAME", "admin")
        valid_pass = os.getenv("ADMIN_PASSWORD", "admin123") # Fallback only for dev

        if username == valid_user and password == valid_pass:
            session['user'] = "admin"
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Username or Password!")
            return redirect(url_for('login'))
            
    return render_template('login.html')

# 4. LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- ADMIN ROUTES (SECURE) ---

# 5. ADMIN DASHBOARD (View & Manage)
@app.route('/admin')
def admin_dashboard():
    # Security Check
    if 'user' not in session:
        return redirect(url_for('login'))

    # Fetch Bills
    bills_list = []
    for doc in db.collection('bills').stream():
        data = doc.to_dict()
        data['id'] = doc.id 
        bills_list.append(data)

    # Fetch MPs (NEW!)
    mps_list = []
    for doc in db.collection('mps').stream():
        data = doc.to_dict()
        data['id'] = doc.id
        mps_list.append(data)
        
    return render_template('admin.html', bills=bills_list, mps=mps_list)

# 6. DELETE BILL
@app.route('/delete_bill/<bill_id>', methods=['POST'])
def delete_bill(bill_id):
    if 'user' not in session: return "Unauthorized", 401
    try:
        db.collection('bills').document(bill_id).delete()
        return "Deleted", 200
    except Exception as e:
        return str(e), 500

# 7. UPDATE BILL STATUS
@app.route('/update_status/<bill_id>/<new_status>', methods=['POST'])
def update_status(bill_id, new_status):
    if 'user' not in session: return "Unauthorized", 401
    try:
        db.collection('bills').document(bill_id).update({'status': new_status})
        return "Updated", 200
    except Exception as e:
        return str(e), 500

# 8. DELETE MP (NEW!)
@app.route('/delete_mp/<mp_id>', methods=['POST'])
def delete_mp(mp_id):
    if 'user' not in session: return "Unauthorized", 401
    try:
        db.collection('mps').document(mp_id).delete()
        return "Deleted", 200
    except Exception as e:
        return str(e), 500

# 9. UPDATE MP ATTENDANCE (NEW!)
@app.route('/update_mp/<mp_id>', methods=['POST'])
def update_mp(mp_id):
    if 'user' not in session: return "Unauthorized", 401
    
    data = request.get_json()
    field = data.get('field') # e.g., 'attendance_pct'
    value = data.get('value') # e.g., 85.5
    
    try:
        db.collection('mps').document(mp_id).update({field: value})
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