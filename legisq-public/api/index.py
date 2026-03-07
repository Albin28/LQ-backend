import os
from flask import Flask, jsonify, render_template, request, session
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

# --- CONFIGURATION ---
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "1230984576-poda-patti-nayyinte-mone")

# --- FIREBASE SETUP ---
db = None
bucket = None
firebase_diagnostic = {"status": "Starting", "errors": []}

try:
    if os.getenv('VERCEL') == '1' or os.getenv('VERCEL_ENV'):
        firebase_diagnostic["env"] = "Vercel"
        cert_json_str = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
        if not cert_json_str:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY is missing from environment variables.")
        
        firebase_diagnostic["key_length"] = len(cert_json_str)
        try:
            cert_json = json.loads(cert_json_str)
            firebase_diagnostic["json_parse"] = "Success"
        except json.JSONDecodeError as je:
            firebase_diagnostic["json_parse"] = f"Failed: {je}"
            raise je

        cred = credentials.Certificate(cert_json)
        project_id = cert_json.get('project_id')
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET') or f"{project_id}.appspot.com"
    else:
        firebase_diagnostic["env"] = "Local"
        cred_path = "ServiceAccountKey.json"
        if not os.path.exists(cred_path):
             raise FileNotFoundError(f"{cred_path} not found.")
        cred = credentials.Certificate(cred_path)
        with open(cred_path) as f:
            cert_json = json.load(f)
        project_id = cert_json.get('project_id')
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET') or f"{project_id}.appspot.com"

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
    
    db = firestore.client()
    firebase_diagnostic["status"] = "Connected"
    
    # Bucket initialization check
    try:
        bucket = storage.bucket()
        # Non-destructive check
        bucket.get_logging() 
        firebase_diagnostic["storage"] = "Connected"
    except Exception as se:
        firebase_diagnostic["storage"] = f"Warning: {se}"
        bucket = None

except Exception as e:
    error_msg = f"Firebase initialization failed: {e}"
    print(f"❌ {error_msg}")
    firebase_diagnostic["status"] = "Failed"
    firebase_diagnostic["errors"].append(str(e))
    app.config['FIREBASE_ERROR'] = error_msg
app.config['FIREBASE_DIAGNOSTIC'] = firebase_diagnostic

# --- RSS FEED SETUP ---
RSS_FEEDS = [
    {"url": "https://feeds.feedburner.com/ndtvnews-top-stories", "source": "NDTV", "class": "ndtv"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "source": "Times of India", "class": "toi"},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "source": "The Hindu", "class": "hindu"},
    {"url": "https://indianexpress.com/section/india/feed/", "source": "Indian Express", "class": "ie"}
]
RSS_CACHE = {'timestamp': 0, 'data': []}
CACHE_DURATION = 900 

def get_rss_news():
    current_time = time.time()
    if current_time - RSS_CACHE['timestamp'] < CACHE_DURATION:
        return RSS_CACHE['data']

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
    return all_news

def format_timestamp(value):
    if hasattr(value, 'to_datetime'):
        value = value.to_datetime()
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    return value

def serialize_bill_doc(doc):
    data = doc.to_dict() or {}
    data['id'] = doc.id
    if 'date_introduced' in data:
        data['date_introduced'] = format_timestamp(data['date_introduced'])
    return data

def serialize_generic_doc(doc):
    data = doc.to_dict() or {}
    data['id'] = doc.id
    return data

# --- DIAGNOSTIC ROUTES ---
@app.route('/health')
def health():
    return jsonify({
        "status": "Alive",
        "firebase": firebase_diagnostic.get("status"),
        "vercel": os.getenv('VERCEL') == '1'
    })

# --- PUBLIC ROUTES ---
@app.route('/')
def home():
    if db is None:
        diag = app.config.get('FIREBASE_DIAGNOSTIC', {})
        error_html = f"""
        <html>
            <body style="font-family: sans-serif; padding: 2rem; background: #0f172a; color: #f1f5f9;">
                <h1 style="color: #ef4444;">Database Connection Error</h1>
                <p>The public site could not connect to Firebase. Please check your Vercel Environment Variables.</p>
                <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
                    <h3>Diagnostic Info:</h3>
                    <pre>{json.dumps(diag, indent=2)}</pre>
                </div>
                <p style="margin-top: 2rem; font-size: 0.9rem; color: #94a3b8;">
                    Tip: Ensure <b>FIREBASE_SERVICE_ACCOUNT_KEY</b> is a valid JSON string without extra newlines.
                </p>
            </body>
        </html>
        """
        return error_html, 500
    
    # Try sorted query first
    docs = db.collection('bills').order_by('date_introduced', direction=firestore.Query.DESCENDING).limit(50).stream()
    bills_list = [serialize_bill_doc(doc) for doc in docs]
    
    # Fallback to unsorted query if 0 results (likely missing date_introduced fields)
    if not bills_list:
        docs = db.collection('bills').limit(50).stream()
        bills_list = [serialize_bill_doc(doc) for doc in docs]
        
    return render_template('index.html', bills=bills_list)

@app.route('/mps')
def mps_dashboard():
    if db is None: return "<h1>Database not connected.</h1>", 500
    
    mps_ref = db.collection('mps')
    docs = mps_ref.stream()
    mps_list = [serialize_generic_doc(doc) for doc in docs]
    
    sessions = sorted(list(set(str(mp.get('session', 'N/A')) for mp in mps_list)))
    houses = sorted(list(set(str(mp.get('house', 'N/A')) for mp in mps_list)))
    states = sorted(list(set(str(mp.get('state', 'N/A')) for mp in mps_list)))
        
    return render_template('mps.html', mps=mps_list, sessions=sessions, houses=houses, states=states)

@app.route('/current_affairs')
def current_affairs():
    news_data = get_rss_news()
    return render_template('current_affairs.html', news=news_data)

# --- ERROR HANDLERS ---
@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, 'code') and e.code < 500:
        return jsonify(error=str(e)), e.code
    
    # Custom 500 error page with diagnostics
    diag = app.config.get('FIREBASE_DIAGNOSTIC', {})
    trace = "No traceback available"
    import traceback
    trace = traceback.format_exc()
    
    error_html = f"""
    <html>
        <body style="font-family: sans-serif; padding: 2rem; background: #0f172a; color: #f1f5f9;">
            <h1 style="color: #ef4444;">Application Error (500)</h1>
            <p>Something went wrong on the server.</p>
            <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155; margin-bottom: 1rem;">
                <h3>Error Details:</h3>
                <pre style="white-space: pre-wrap; color: #fca5a5;">{str(e)}</pre>
            </div>
            <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
                <h3>Diagnostic Info:</h3>
                <pre>{json.dumps(diag, indent=2)}</pre>
            </div>
            <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155; margin-top:1rem;">
                <h3>Traceback:</h3>
                <pre style="font-size: 0.8rem; color: #94a3b8;">{trace}</pre>
            </div>
        </body>
    </html>
    """
    return error_html, 500

# This is the entry point for Vercel
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)
