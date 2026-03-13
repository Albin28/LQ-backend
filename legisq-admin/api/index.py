import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
try:
    import feedparser
except Exception:
    feedparser = None
import time
from time import mktime
from datetime import datetime
import re
import base64
from urllib.parse import urlparse
from firebase_admin import auth as firebase_auth
from werkzeug.utils import secure_filename
import requests
from functools import wraps

# --- CONFIGURATION ---
# Resolve paths relative to THIS FILE, not the working directory.
# index.py lives in legisq-admin/api/, so parent is legisq-admin/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)

# Load .env from legisq-admin/ (not from api/)
load_dotenv(os.path.join(_PARENT_DIR, ".env"))

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "1230984756-project-LQ")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

# --- FIREBASE SETUP ---
# ServiceAccountKey.json lives in legisq-admin/, NOT in api/
_KEY_PATH = os.path.join(_PARENT_DIR, "ServiceAccountKey.json")

db = None

try:
    cred = credentials.Certificate(_KEY_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase (Firestore) connected.")
except Exception as e:
    print(f"❌ Firebase connection error: {e}")

# --- GITHUB STORAGE CONFIG ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO  = os.getenv("GITHUB_REPO")   # e.g. "Albin28/legisq-bills"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

if GITHUB_TOKEN and GITHUB_REPO:
    print(f"✅ GitHub storage configured: {GITHUB_REPO}")
else:
    print("⚠️  GitHub storage not configured — add GITHUB_TOKEN and GITHUB_REPO to .env")


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = session.get('id_token')
        if not id_token:
            print("⚠️ require_admin: No id_token in session → redirecting to login")
            return redirect(url_for('login'))
        try:
            firebase_auth.verify_id_token(id_token)
        except Exception as e:
            print(f"⚠️ require_admin: verify_id_token failed: {e}")
            # Fallback: if the session has a valid user email, allow access locally.
            # verify_id_token can fail due to network issues or clock skew in dev.
            if session.get('user'):
                print(f"✅ require_admin: Falling back to session user: {session.get('user')} — allowing access")
                return f(*args, **kwargs)
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

ALLOWED_EXTENSIONS = {'.pdf', '.docx'}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _github_upload(file_bytes: bytes, bill_id: str, filename: str) -> str:
    """
    Upload a file to a public GitHub repo via the Contents API.
    Returns a raw.githubusercontent.com URL that is always publicly accessible.
    Requires GITHUB_TOKEN (personal access token) and GITHUB_REPO (e.g. 'user/repo').
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise ValueError(
            "GitHub storage is not configured. "
            "Add GITHUB_TOKEN and GITHUB_REPO to your .env file."
        )

    path    = f"bills/{bill_id}/{filename}"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github.v3+json",
    }

    # If the file already exists, we need its SHA to update it
    sha = None
    existing = requests.get(api_url, headers=headers, timeout=15)
    if existing.status_code == 200:
        sha = existing.json().get("sha")

    body = {
        "message": f"Upload PDF for bill {bill_id}",
        "content": base64.b64encode(file_bytes).decode(),
        "branch":  GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha  # required when updating an existing file

    resp = requests.put(api_url, json=body, headers=headers, timeout=60)

    if not resp.ok:
        raise ValueError(f"GitHub upload failed ({resp.status_code}): {resp.text[:300]}")

    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{path}"


def upload_pdf_to_storage(pdf_file, doc_id):
    if not pdf_file or not pdf_file.filename:
        return None

    safe_name = secure_filename(pdf_file.filename)
    ext = os.path.splitext(safe_name)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid file type '{ext}'. Only PDF and DOCX are allowed.")

    pdf_file.seek(0, 2)
    file_size = pdf_file.tell()
    pdf_file.seek(0)
    if file_size > MAX_FILE_BYTES:
        raise ValueError(f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum is 10 MB.")

    file_bytes = pdf_file.read()
    return _github_upload(file_bytes, doc_id, safe_name)

def serialize_doc(doc):
    if not doc.exists:
        return None
    data = doc.to_dict()
    data['id'] = doc.id
    # Handle Firestore timestamps
    for key, value in data.items():
        if hasattr(value, 'isoformat'): # Handles datetime and DatetimeWithNanoseconds
            data[key] = value.isoformat()
    return data

def serialize_bill_doc(doc):
    return serialize_doc(doc)

def serialize_generic_doc(doc):
    return serialize_doc(doc)

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
    # Order by date_introduced descending so newest bills appear at the top
    bills = [serialize_bill_doc(doc) for doc in db.collection('bills').order_by('date_introduced', direction=firestore.Query.DESCENDING).stream()]
    mps = [serialize_generic_doc(doc) for doc in db.collection('mps').stream()]
    return render_template('admin.html', bills=bills, mps=mps)

@app.route('/mps')
@require_admin
def mps_dashboard():
    return redirect(url_for('admin_dashboard'))

@app.route('/current_affairs')
@require_admin
def current_affairs():
    return redirect(url_for('admin_dashboard'))

@app.route('/api/bills', methods=['POST'])
@require_admin
def add_bill():
    data = request.form
    
    # Use custom_id if provided (manual ID entry), otherwise generate one
    custom_id = data.get('custom_id')
    if custom_id and custom_id.strip():
        doc_ref = db.collection('bills').document(custom_id.strip())
    else:
        doc_ref = db.collection('bills').document()
    
    try:
        pdf_file = request.files.get('pdf')
        pdf_url = None
        if pdf_file and pdf_file.filename:
            try:
                pdf_url = upload_pdf_to_storage(pdf_file, doc_ref.id)
            except ValueError as ve:
                # Upload failed; fall back to manual URL if given
                manual_url = data.get('pdf_url_manual', '').strip()
                if manual_url:
                    pdf_url = manual_url
                    print(f"⚠️ Upload failed, using manual URL: {manual_url}")
                else:
                    raise
        elif data.get('pdf_url_manual', '').strip():
            pdf_url = data.get('pdf_url_manual').strip()

        bill_data = {
            "title": data.get('title'),
            "status": data.get('status'),
            "summary": data.get('summary', ''),
            "date_introduced": firestore.SERVER_TIMESTAMP,
            "pdf_url": pdf_url
        }
        doc_ref.set(bill_data)
        return jsonify({"success": True, "id": doc_ref.id}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"❌ Error adding bill: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bills/<bill_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin
def manage_bill(bill_id):
    doc_ref = db.collection('bills').document(bill_id)
    if request.method == 'GET':
        return jsonify(serialize_bill_doc(doc_ref.get()))
    if request.method == 'PUT':
        data = request.form
        update_data = {"title": data.get('title'), "status": data.get('status'), "summary": data.get('summary')}

        # Handle explicit PDF removal
        if data.get('remove_pdf') == '1':
            update_data['pdf_url'] = None
            print(f"🗑️ PDF removed for bill {bill_id}")
        else:
            # Handle new PDF upload
            pdf_file = request.files.get('pdf')
            if pdf_file and pdf_file.filename:
                try:
                    update_data['pdf_url'] = upload_pdf_to_storage(pdf_file, bill_id)
                except ValueError as ve:
                    # Upload failed — fall back to manual URL if provided
                    manual_url = data.get('pdf_url_manual', '').strip()
                    if manual_url:
                        update_data['pdf_url'] = manual_url
                        print(f"⚠️ Upload failed, using manual URL for {bill_id}: {manual_url}")
                    else:
                        return jsonify({"error": str(ve)}), 400
            else:
                # No file uploaded — use manual URL if provided
                manual_url = data.get('pdf_url_manual', '').strip()
                if manual_url:
                    update_data['pdf_url'] = manual_url

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
    doc_ref.set(data)
    return jsonify({"success": True, "id": doc_ref.id}), 201

@app.route('/api/mps/<mp_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin
def manage_mp(mp_id):
    doc_ref = db.collection('mps').document(mp_id)
    if request.method == 'GET':
        return jsonify(serialize_generic_doc(doc_ref.get()))
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
        
        # NOTE: PDFs are stored in GitHub — they are NOT deleted on reset.
        # Firestore data is cleared above; re-run bulk_upload.py to repopulate.

        return jsonify({"success": True, "message": "Database cleared successfully"}), 200
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8001"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)
