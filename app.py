import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_from_directory
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURATION ---
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "legisq_local_dev_key")

# --- FIREBASE SETUP (Local only - uses serviceAccountKey.json) ---
db = None

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase connected")
except Exception as e:
    print(f"❌ Firebase error: {e}")


# --- PUBLIC ROUTES ---

# 1. HOME PAGE (Bills Dashboard)
@app.route('/')
def home():
    if db is None:
        return "<h1>Database not connected</h1><p>Check serviceAccountKey.json and restart the app.</p>"

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
    # Sets for unique filter values
    sessions = set()
    houses = set()
    states = set()

    for doc in docs:
        data = doc.to_dict()
        mps_list.append(data)
        
        # Collect unique values for filters
        if data.get('session'): sessions.add(data.get('session'))
        if data.get('house'): houses.add(data.get('house'))
        if data.get('state'): states.add(data.get('state'))
        
    return render_template('mps.html', 
                           mps=mps_list,
                           sessions=sorted(list(sessions)),
                           houses=sorted(list(houses)),
                           states=sorted(list(states)))

# --- RSS FEED SETUP ---
try:
    import feedparser
except ImportError:
    feedparser = None
    print("⚠️ Warning: feedparser module not found or incompatible (missing cgi). RSS feeds disabled.")
import time
from time import mktime
from datetime import datetime

RSS_FEEDS = [
    {"url": "https://feeds.feedburner.com/ndtvnews-top-stories", "source": "NDTV", "class": "ndtv"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "source": "Times of India", "class": "toi"},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "source": "The Hindu", "class": "hindu"},
    {"url": "https://indianexpress.com/section/india/feed/", "source": "Indian Express", "class": "ie"},
    {"url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "source": "Hindustan Times", "class": "ht"},
    {"url": "https://www.news18.com/commonfeeds/v1/en/rss/india.xml", "source": "News18", "class": "news18"},
    {"url": "https://zeenews.india.com/rss/india-national-news.xml", "source": "Zee News", "class": "zee"}
]

RSS_CACHE_FILE = "rss_cache.json"
CACHE_DURATION = 900  # 15 minutes in seconds

def get_rss_news():
    # 1. Check Cache
    if os.path.exists(RSS_CACHE_FILE):
        try:
            current_time = time.time()
            file_mod_time = os.path.getmtime(RSS_CACHE_FILE)
            
            if current_time - file_mod_time < CACHE_DURATION:
                with open(RSS_CACHE_FILE, 'r') as f:
                    print("✅ Serving News from Cache")
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Cache Read Error: {e}")

    # 2. Fetch from Feeds
    if not feedparser:
        print("❌ Feedparser not available. Skipping RSS fetch.")
        return []

    print("🌍 Fetching News from RSS Feeds...")
    all_news = []
    
    for feed in RSS_FEEDS:
        try:
            parsed_feed = feedparser.parse(feed['url'])
            
            # Limit to top 3 entries per feed to keep it balanced
            for entry in parsed_feed.entries[:3]:
                # Image Extraction Logic (Best Effort)
                image_url = None
                
                # Method A: Media Content (Standard RSS/Atom)
                if 'media_content' in entry:
                    image_url = entry.media_content[0]['url']
                
                # Method B: Enclosures (Podcasts/Some News)
                elif 'media_thumbnail' in entry:
                     image_url = entry.media_thumbnail[0]['url']
                
                # Method C: Parse Description for <img> tag (Common in old RSS)
                elif 'summary' in entry and '<img' in entry.summary:
                    import re
                    match = re.search(r'src="([^"]+)"', entry.summary)
                    if match:
                        image_url = match.group(1)

                # Date Formatting
                published_str = "Recent"
                try:
                    if hasattr(entry, 'published_parsed'):
                        dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                        published_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass

                all_news.append({
                    'headline': entry.title,
                    'link': entry.link,
                    'summary': entry.summary.split('<')[0][:200] + "..." if 'summary' in entry else "", # Strip HTML tags roughly
                    'date': published_str,
                    'source': feed['source'],
                    'source_class': feed['class'],
                    'image': image_url
                })
                
        except Exception as e:
            print(f"❌ Failed to fetch {feed['source']}: {e}")

    # 3. Sort & Save Cache
    # Sort by date ? Difficult with mixed formats, leaving as aggregated list for now or randomize
    # all_news.sort(key=lambda x: x['date'], reverse=True) 
    
    try:
        with open(RSS_CACHE_FILE, 'w') as f:
            json.dump(all_news, f)
            print("💾 Saved News to Cache")
    except Exception as e:
        print(f"⚠️ Cache Write Error: {e}")
        
    return all_news

# 3. CURRENT AFFAIRS PAGE (RSS)
@app.route('/current_affairs')
def current_affairs():
    news_data = get_rss_news()
    return render_template('current_affairs.html', news=news_data)

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

# 10. ADD BILL (NEW!)
@app.route('/add_bill', methods=['POST'])
def add_bill():
    if 'user' not in session: return "Unauthorized", 401
    
    try:
        # Changed to handle Form Data (File Upload)
        title = request.form.get('title')
        category = request.form.get('category', 'General')
        date_intro = request.form.get('date_introduced', '')
        
        # Simple ID generation
        import re
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', title.strip().replace(" ", "_"))
        
        # 1. Handle File Upload
        file_path = ''
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                # FORCE filename to match ID (Terminology Rule)
                filename = f"{safe_id}.pdf"
                save_path = os.path.join("static/dataset", filename)
                file.save(save_path)
                file_path = filename

        bill_data = {
            'title': title,
            'category': category,
            'date_introduced': date_intro,
            'status': 'Pending',
            # REMOVED: Summary field (User Request)
            'file_path': file_path 
        }
        
        db.collection('bills').document(safe_id).set(bill_data)
        return "Added", 200
    except Exception as e:
        return str(e), 500

# 11. ADD MP (NEW!)
@app.route('/add_mp', methods=['POST'])
def add_mp():
    if 'user' not in session: return "Unauthorized", 401
    
    try:
        data = request.get_json()
        name = data.get('name')
        session_name = data.get('session')
        
        # ID generation
        import re
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', f"{name}_{session_name}".strip().replace(" ", "_"))
        
        # Calculations
        days = int(data.get('days_attended', 0))
        total = int(data.get('total_days', 1))
        pct = round((days / total) * 100, 1) if total > 0 else 0
        
        mp_data = {
            'name': name,
            'state': data.get('state', ''),
            'house': data.get('house', 'Lok Sabha'),
            'constituency': data.get('constituency', ''),
            'session': session_name,
            'days_attended': days,
            'total_days': total,
            'attendance_pct': pct,
            'questions': int(data.get('questions', 0)),
            'debates': int(data.get('debates', 0))
        }
        
        db.collection('mps').document(safe_id).set(mp_data)
        return "Added", 200
    except Exception as e:
        return str(e), 500

# --- HELPER API ---
@app.route('/api/bills')
def get_bills_json():
    docs = db.collection('bills').stream()
    return jsonify([doc.to_dict() for doc in docs])

@app.route('/download/<path:filename>')
def download_bill(filename):
    # Security: Ensure we only serve from static/dataset
    directory = os.path.join(app.root_path, 'static', 'dataset')
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)