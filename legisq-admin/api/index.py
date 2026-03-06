import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage
from dotenv import load_dotenv
try:
    import feedparser
except Exception:
    feedparser = None
import time
from time import mktime
from datetime import datetime
import re
from urllib.parse import urlparse
from firebase_admin import auth as firebase_auth
from werkzeug.utils import secure_filename
import requests
from functools import wraps

# --- CONFIGURATION ---
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "1230984576-poda-patti-nayyinte-mone")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

# --- FIREBASE SETUP ---
db = None
bucket = None
try:
    # Admin app always uses ServiceAccountKey.json locally
    cred = credentials.Certificate("ServiceAccountKey.json")
    with open("ServiceAccountKey.json") as f:
        cert_json = json.load(f)
    project_id = cert_json.get('project_id')
    bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET') or f"{project_id}.appspot.com"

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
    
    db = firestore.client()
    bucket = storage.bucket()
    print(f"✅ Firebase (Admin) connected. Bucket: {bucket_name}")
except Exception as e:
    print(f"❌ Firebase connection error: {e}")

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = session.get('id_token')
        if not id_token:
            return redirect(url_for('login'))
        try:
            firebase_auth.verify_id_token(id_token)
        except:
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def upload_pdf_to_storage(pdf_file, doc_id):
    if not bucket or not pdf_file or not pdf_file.filename:
        return None
    safe_name = secure_filename(pdf_file.filename)
    filename = f"bills/{doc_id}/{int(time.time())}_{safe_name}"
    blob = bucket.blob(filename)
    blob.upload_from_file(pdf_file, content_type='application/pdf')
    blob.make_public()
    return blob.public_url

def serialize_bill_doc(doc):
    data = doc.to_dict() or {}
    data['id'] = doc.id
    return data

def serialize_generic_doc(doc):
    data = doc.to_dict() or {}
    data['id'] = doc.id
    return data

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('password')
        payload = {"email": email, "password": password, "returnSecureToken": True}
        resp = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}", json=payload)
        data = resp.json()
        if resp.ok:
            session['user'] = email
            session['id_token'] = data.get('idToken')
            return redirect(url_for('admin_dashboard'))
        flash("Invalid Credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@app.route('/')
@require_admin
def admin_dashboard():
    bills = [serialize_bill_doc(doc) for doc in db.collection('bills').stream()]
    mps = [serialize_generic_doc(doc) for doc in db.collection('mps').stream()]
    return render_template('admin.html', bills=bills, mps=mps)

@app.route('/api/bills', methods=['POST'])
@require_admin
def add_bill():
    data = request.form
    doc_ref = db.collection('bills').document()
    pdf_file = request.files.get('pdf')
    pdf_url = upload_pdf_to_storage(pdf_file, doc_ref.id)
    
    bill_data = {
        "title": data.get('title'),
        "status": data.get('status'),
        "summary": data.get('summary', ''),
        "date_introduced": firestore.SERVER_TIMESTAMP,
        "pdf_url": pdf_url
    }
    doc_ref.set(bill_data)
    return jsonify({"success": True}), 201

@app.route('/api/bills/<bill_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin
def manage_bill(bill_id):
    doc_ref = db.collection('bills').document(bill_id)
    if request.method == 'GET':
        return jsonify(serialize_bill_doc(doc_ref.get()))
    if request.method == 'PUT':
        data = request.form
        update_data = {"title": data.get('title'), "status": data.get('status'), "summary": data.get('summary')}
        pdf_file = request.files.get('pdf')
        if pdf_file:
            update_data['pdf_url'] = upload_pdf_to_storage(pdf_file, bill_id)
        doc_ref.update(update_data)
        return jsonify({"success": True})
    if request.method == 'DELETE':
        doc_ref.delete()
        return jsonify({"success": True})

@app.route('/api/mps', methods=['POST'])
@require_admin
def add_mp():
    data = request.json
    doc_ref = db.collection('mps').document()
    data['id'] = doc_ref.id
    doc_ref.set(data)
    return jsonify(data), 201

@app.route('/api/mps/<mp_id>', methods=['PUT', 'DELETE'])
@require_admin
def manage_mp(mp_id):
    doc_ref = db.collection('mps').document(mp_id)
    if request.method == 'PUT':
        doc_ref.update(request.json)
        return jsonify({"success": True})
    if request.method == 'DELETE':
        doc_ref.delete()
        return jsonify({"success": True})

@app.route('/api/admin/reset_database', methods=['POST'])
@require_admin
def reset_database_api():
    try:
        # 1. Clear Firestore collections
        collections = ['bills', 'mps']
        for coll_name in collections:
            coll_ref = db.collection(coll_name)
            docs = coll_ref.limit(500).stream()
            for doc in docs:
                doc.reference.delete()
        
        # 2. Clear Storage (bills/ folder)
        if bucket:
            blobs = bucket.list_blobs(prefix='bills/')
            for blob in blobs:
                blob.delete()
        
        return jsonify({"success": True, "message": "Database and Storage cleared successfully"}), 200
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8001)
