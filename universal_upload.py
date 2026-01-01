import sqlite3
import pandas as pd
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- Configuration ---
DATASET_FOLDER = "dataset"
EXCEL_FILE = "bills_metadata.xlsx"  # <--- UPDATED NAME
SQLITE_DB_NAME = "legisq_data.db"
FIREBASE_KEY = "serviceAccountKey.json" # Ensure this file exists in your folder!
FIREBASE_COLLECTION = "legislation"

def init_sqlite():
    """Initializes the local SQLite DB for Android."""
    conn = sqlite3.connect(SQLITE_DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS legislation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            status TEXT,
            date_introduced TEXT,
            file_path TEXT,
            summary TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[SQLite] Database {SQLITE_DB_NAME} initialized.")

def init_firebase():
    """Initializes connection to Firebase for Website."""
    if not os.path.exists(FIREBASE_KEY):
        print(f"[Firebase] WARNING: '{FIREBASE_KEY}' not found.")
        print("   -> Your WEBSITE will NOT be updated.")
        print("   -> (Android database will still be generated.)")
        return None
    
    try:
        # Check if app is already initialized to avoid errors
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_KEY)
            app = firebase_admin.initialize_app(cred)
            print(f"[Firebase] Connected to project: {app.project_id}") # <--- PRINTS YOUR PROJECT NAME
        
        return firestore.client()
    except Exception as e:
        print(f"[Firebase] Connection Failed: {e}")
        return None

def clean_date(date_val):
    """Standardizes dates to YYYY-MM-DD."""
    if pd.isna(date_val) or str(date_val).strip().lower() == "undefined" or str(date_val).strip() == "":
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return pd.to_datetime(date_val).strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def universal_upload():
    """Reads Excel and uploads to BOTH SQLite (Android) and Firebase (Web)."""
    
    excel_path = os.path.join(DATASET_FOLDER, EXCEL_FILE)
    if not os.path.exists(excel_path):
        print(f"ERROR: Could not find {EXCEL_FILE} in '{DATASET_FOLDER}' folder.")
        print("Please move your Excel file into the 'dataset' folder.")
        return

    print("Reading Excel file...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # 1. Setup SQLite (Clear old data)
    conn = sqlite3.connect(SQLITE_DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM legislation') 
    c.execute('DELETE FROM sqlite_sequence WHERE name="legislation"')

    # 2. Setup Firebase (Clear old data)
    db_firestore = init_firebase()
    if db_firestore:
        print("[Firebase] Deleting old documents to avoid duplicates...")
        docs = db_firestore.collection(FIREBASE_COLLECTION).stream()
        for doc in docs:
            doc.reference.delete()
    
    print(f"Processing {len(df)} rows...")

    for index, row in df.iterrows():
        title = row.get('Title', 'Untitled')
        category = row.get('Category', 'General')
        status = row.get('Status', 'Pending')
        
        raw_date = row.get('Date Introduced', '')
        date_introduced = clean_date(raw_date)

        filename = row.get('Filename', '')
        # Path for Android (relative to assets)
        file_path_local = f"dataset/{filename}" if filename else ""
        
        summary = "Summary not available." # No API used

        # --- A. Insert into SQLite (Android) ---
        c.execute('''
            INSERT INTO legislation (title, category, status, date_introduced, file_path, summary)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, category, status, date_introduced, file_path_local, summary))

        # --- B. Insert into Firebase (Website) ---
        if db_firestore:
            doc_data = {
                "title": title,
                "category": category,
                "status": status,
                "date_introduced": date_introduced,
                "file_path": filename, 
                "summary": summary
            }
            db_firestore.collection(FIREBASE_COLLECTION).add(doc_data)

        print(f"Uploaded: {title}")

    # Commit SQLite
    conn.commit()
    conn.close()
    print("------------------------------------------------")
    print("Success! Data synced.")
    print(f"1. [Android] Saved to {SQLITE_DB_NAME}")
    if db_firestore:
        print("2. [Website] Uploaded to Firebase Firestore")
    else:
        print("2. [Website] SKIPPED (Key file missing)")

if __name__ == "__main__":
    init_sqlite()
    universal_upload()