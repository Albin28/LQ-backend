import os
from flask import Flask, render_template, session, flash, send_from_directory
import json

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "legisq_local_dev_key")

# --- MOCK DATA (Replaces Firebase) ---
BILLS_DATA = [
    {
        'title': 'The Fictional Infrastructure Bill',
        'status': 'Pending',
        'category': 'Infrastructure',
        'date_introduced': '2023-01-15',
        'summary': 'A bill to fund imaginary bridges and tunnels.',
        'file_path': ''
    },
    {
        'title': 'The Digital Privacy Act of 2023',
        'status': 'Passed',
        'category': 'Technology',
        'date_introduced': '2023-02-20',
        'summary': 'An act to protect citizens\' data in the digital realm.',
        'file_path': ''
    }
]

MPS_DATA = [
    {
        'name': 'John Doe',
        'state': 'California',
        'house': 'House of Representatives',
        'constituency': 'District 1',
        'session': '118th Congress',
        'days_attended': 150,
        'total_days': 160,
        'attendance_pct': 93.8,
        'questions': 25,
        'debates': 10
    },
    {
        'name': 'Jane Smith',
        'state': 'New York',
        'house': 'Senate',
        'constituency': 'Statewide',
        'session': '118th Congress',
        'days_attended': 155,
        'total_days': 160,
        'attendance_pct': 96.9,
        'questions': 30,
        'debates': 12
    }
]

# --- PUBLIC ROUTES ---

# 1. HOME PAGE (Bills Dashboard)
@app.route('/')
def home():
    return render_template('index.html', bills=BILLS_DATA)

# 2. MP DASHBOARD (Public View)
@app.route('/mps')
def mps_dashboard():
    # Unique filter values from mock data
    sessions = set(mp['session'] for mp in MPS_DATA)
    houses = set(mp['house'] for mp in MPS_DATA)
    states = set(mp['state'] for mp in MPS_DATA)
        
    return render_template('mps.html', 
                           mps=MPS_DATA,
                           sessions=sorted(list(sessions)),
                           houses=sorted(list(houses)),
                           states=sorted(list(states)))

# 3. CURRENT AFFAIRS PAGE (RSS) - Now a placeholder
@app.route('/current_affairs')
def current_affairs():
    # RSS feed functionality is removed, we can pass empty data or a message
    return render_template('current_affairs.html', news=[])

# 4. LOGIN PAGE - Now a placeholder
@app.route('/login')
def login():
    flash("Login is disabled in this version.")
    return render_template('login.html')

# 5. ADMIN DASHBOARD - Now a placeholder
@app.route('/admin')
def admin_dashboard():
    # Admin functionality is removed
    return render_template('admin.html', bills=[], mps=[])

# --- STATIC FILE SERVING ---
@app.route('/download/<path:filename>')
def download_bill(filename):
    # This route is now a placeholder as file handling is removed
    directory = os.path.join(app.root_path, 'static', 'dataset')
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)