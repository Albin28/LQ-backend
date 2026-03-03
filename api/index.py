import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_from_directory
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import feedparser
import time
from time import mktime
from datetime import datetime
import re

from werkzeug.utils import secure_filename

# --- CONFIGURATION ---
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a_strong_default_secret_key")
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'dataset')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# --- FIREBASE SETUP ---
db = None
try:
    # Vercel will use environment variables, local will use the file
    if os.getenv('VERCEL_ENV') == 'production':
        cert_json = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'))
        cred = credentials.Certificate(cert_json)
    else:
        # Local development
        cred = credentials.Certificate("serviceAccountKey.json")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    print("✅ Firebase connected successfully.")
except Exception as e:
    print(f"❌ Firebase connection error: {e}")
    # You might want to handle this more gracefully
    # For now, the app will continue but database-dependent routes will fail.

# --- RSS FEED SETUP ---
RSS_FEEDS = [
    {"url": "https://feeds.feedburner.com/ndtvnews-top-stories", "source": "NDTV", "class": "ndtv"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "source": "Times of India", "class": "toi"},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "source": "The Hindu", "class": "hindu"},
    {"url": "https://indianexpress.com/section/india/feed/", "source": "Indian Express", "class": "ie"}
]
RSS_CACHE = {'timestamp': 0, 'data': []}
CACHE_DURATION = 900  # 15 minutes

def get_rss_news():
    current_time = time.time()
    if current_time - RSS_CACHE['timestamp'] < CACHE_DURATION:
        print("✅ Serving News from Cache")
        return RSS_CACHE['data']

    print("🌍 Fetching News from RSS Feeds...")
    all_news = []
    for feed in RSS_FEEDS:
        try:
            parsed_feed = feedparser.parse(feed['url'])
            for entry in parsed_feed.entries[:3]:
                image_url = None
                if 'media_content' in entry:
                    image_url = entry.media_content[0]['url']
                elif 'media_thumbnail' in entry:
                    image_url = entry.media_thumbnail[0]['url']
                
                published_str = "Recent"
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    published_str = dt.strftime("%b %d, %Y")

                all_news.append({
                    'headline': entry.title,
                    'link': entry.link,
                    'summary': re.sub('<[^<]+?>', '', entry.summary)[:120] + "..." if 'summary' in entry else "",
                    'date': published_str,
                    'source': feed['source'],
                    'source_class': feed['class'],
                    'image': image_url
                })
        except Exception as e:
            print(f"❌ Failed to fetch {feed['source']}: {e}")
    
    RSS_CACHE['timestamp'] = current_time
    RSS_CACHE['data'] = all_news
    print("💾 Saved News to Cache")
    return all_news

# --- PUBLIC ROUTES ---
@app.route('/')
def home():
    if db is None:
        return "<h1>Database not connected. Check logs for errors.</h1>", 500
    
    bills_ref = db.collection('bills').order_by('date_introduced', direction=firestore.Query.DESCENDING).limit(50)
    docs = bills_ref.stream()
    bills_list = [doc.to_dict() for doc in docs]
    return render_template('index.html', bills=bills_list)

@app.route('/mps')
def mps_dashboard():
    if db is None: return "<h1>Database not connected.</h1>", 500
    
    mps_ref = db.collection('mps')
    docs = mps_ref.stream()
    mps_list = [doc.to_dict() for doc in docs]
    
    sessions = sorted(list(set(mp.get('session', 'N/A') for mp in mps_list)))
    houses = sorted(list(set(mp.get('house', 'N/A') for mp in mps_list)))
    states = sorted(list(set(mp.get('state', 'N/A') for mp in mps_list)))
        
    return render_template('mps.html', mps=mps_list, sessions=sessions, houses=houses, states=states)

@app.route('/current_affairs')
def current_affairs():
    news_data = get_rss_news()
    return render_template('current_affairs.html', news=news_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        valid_user = os.getenv("ADMIN_USERNAME", "admin")
        valid_pass = os.getenv("ADMIN_PASSWORD", "admin123")

        if username == valid_user and password == valid_pass:
            session['user'] = "admin"
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for('login'))
    
    # If already logged in, redirect to admin
    if 'user' in session:
        return redirect(url_for('admin_dashboard'))
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- ADMIN ROUTES (SECURE) ---
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    if db is None: return "<h1>Database not connected.</h1>", 500

    bills_list = [doc.to_dict() for doc in db.collection('bills').stream()]
    mps_list = [doc.to_dict() for doc in db.collection('mps').stream()]
    return render_template('admin.html', bills=bills_list, mps=mps_list)

# --- API ROUTES ---
@app.route('/api/bills', methods=['POST'])
def add_bill():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.form
        bill_no = data.get('bill_no')
        if not bill_no or not data.get('title') or not data.get('status'):
            return jsonify({"error": "Missing required fields: bill_no, title, status"}), 400
        
        doc_ref = db.collection('bills').document(str(bill_no))
        
        pdf_url = None
        if 'pdf' in request.files:
            pdf_file = request.files['pdf']
            if pdf_file.filename != '':
                # Use bill_no for the filename to ensure uniqueness
                filename = f"{str(bill_no)}.pdf"
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf_file.save(pdf_path)
                pdf_url = url_for('static', filename=f'dataset/{filename}', _external=True)

        bill_data = {
            "bill_no": bill_no,
            "title": data['title'],
            "status": data['status'],
            "summary": data.get('summary', ''),
            "house": data.get('house', ''),
            "date_introduced": firestore.SERVER_TIMESTAMP,
        }
        if pdf_url:
            bill_data["pdf_url"] = pdf_url
        
        doc_ref.set(bill_data, merge=True)
        return jsonify(bill_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bills/<bill_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_bill(bill_id):
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    doc_ref = db.collection('bills').document(bill_id)

    if request.method == 'GET':
        doc = doc_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict())
        else:
            return jsonify({"error": "Not Found"}), 404

    if request.method == 'PUT':
        try:
            data = request.json
            doc_ref.update(data)
            return jsonify({"id": bill_id, **data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            return jsonify({"success": True, "id": bill_id}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/mps/<mp_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_mp(mp_id):
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    doc_ref = db.collection('mps').document(mp_id)

    if request.method == 'GET':
        doc = doc_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict())
        else:
            return jsonify({"error": "Not Found"}), 404

    if request.method == 'PUT':
        try:
            data = request.json
            # Convert numeric fields from string
            for field in ['attendance_pct', 'questions', 'debates']:
                if field in data and data[field]:
                    data[field] = float(data[field]) if '.' in data[field] else int(data[field])
            doc_ref.update(data)
            return jsonify({"id": mp_id, **data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            return jsonify({"success": True, "id": mp_id}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/mps', methods=['POST'])
def add_mp():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.json
        if not data.get('name') or not data.get('state'):
            return jsonify({"error": "Missing required fields"}), 400
        
        doc_ref = db.collection('mps').document(data.get('id') or None)
        
        mp_data = {
            "id": doc_ref.id,
            "name": data['name'],
            "state": data['state'],
            "constituency": data.get('constituency', ''),
            "house": data.get('house', 'Lok Sabha'),
            "attendance_pct": float(data.get('attendance_pct', 0)),
            "questions": int(data.get('questions', 0)),
            "debates": int(data.get('debates', 0)),
            "session": data.get('session', '17th Lok Sabha'),
        }
        doc_ref.set(mp_data)
        return jsonify(mp_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# This is the entry point for Vercel
if __name__ == '__main__':
    app.run(debug=True)
