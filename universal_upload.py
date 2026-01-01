import sqlite3
import pandas as pd
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- Configuration ---
DATASET_FOLDER = "static/dataset"
EXCEL_FILE = "bills_metadata.xlsx" 
SQLITE_DB_NAME = "legisq_data.db"
FIREBASE_KEY = "serviceAccountKey.json"

def init_sqlite():
    """
    Initializes the local SQLite DB.
    CRITICAL CHANGE: drops old tables to enforce new schema (TEXT IDs).
    """
    conn = sqlite3.connect(SQLITE_DB_NAME)
    c = conn.cursor()
    
    print("[SQLite] Resetting database tables...")
    # Wipe old tables so we don't get 'datatype mismatch' errors
    c.execute('DROP TABLE IF EXISTS bills')
    c.execute('DROP TABLE IF EXISTS mps')
    
    # Create Table 1: bills (bill_id is TEXT)
    c.execute('''
        CREATE TABLE bills (
            bill_id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            status TEXT,
            date_introduced TEXT,
            file_path TEXT,
            summary TEXT
        )
    ''')
    
    # Create Table 2: mps (mp_id is TEXT)
    c.execute('''
        CREATE TABLE mps (
            mp_id TEXT PRIMARY KEY,
            name TEXT,
            constituency TEXT,
            party TEXT,
            performance_score TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[SQLite] Database {SQLITE_DB_NAME} ready with correct schema.")

def init_firebase():
    """Initializes connection to Firebase."""
    if not os.path.exists(FIREBASE_KEY):
        print(f"[Firebase] WARNING: '{FIREBASE_KEY}' missing. Skipping cloud upload.")
        return None
    
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_KEY)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"[Firebase] Connection Error: {e}")
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
    # 1. Initialize DBs (This fixes the schema error)
    init_sqlite()
    db_firestore = init_firebase()

    # 2. Check Excel
    excel_path = os.path.join(DATASET_FOLDER, EXCEL_FILE)
    if not os.path.exists(excel_path):
        print(f"ERROR: Could not find {EXCEL_FILE} in '{DATASET_FOLDER}'.")
        return

    print(f"Reading {EXCEL_FILE}...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # 3. Decision Logic
    first_col = df.columns[0].strip()
    print(f"--> First Column Found: '{first_col}'")

    if first_col == 'Bill_id':
        mode = 'BILLS'
        collection_name = 'bills'
        table_name = 'bills'
    elif first_col == 'MP_id':
        mode = 'MPS'
        collection_name = 'mps'
        table_name = 'mps'
    else:
        print(f"ERROR: First column is '{first_col}'. It must be 'Bill_id' or 'MP_id'.")
        return

    print(f"--> Mode Detected: {mode}. Syncing to collection '{collection_name}'...")

    # 4. Clear Firebase Collection (Optional - prevents duplicates)
    if db_firestore:
        docs = db_firestore.collection(collection_name).stream()
        for doc in docs:
            doc.reference.delete()

    # 5. Process Rows
    conn = sqlite3.connect(SQLITE_DB_NAME)
    c = conn.cursor()
    
    count = 0
    for index, row in df.iterrows():
        
        # Get ID as String (Crucial fix)
        row_id = str(row[first_col]).strip()

        if mode == 'BILLS':
            title = row.get('Title', 'Untitled')
            category = row.get('Category', 'General')
            status = row.get('Status', 'Pending')
            date_introduced = clean_date(row.get('Date Introduced', ''))
            
            # Filename Logic: "Bill_001" -> "Bill_001.pdf"
            filename = f"{row_id}.pdf"
            
            # Check if file exists
            full_file_path = os.path.join(DATASET_FOLDER, filename)
            
            # Fallback check (in case file is named Bill_Bill_001 or similar)
            if not os.path.exists(full_file_path) and not row_id.lower().startswith('bill'):
                 filename = f"Bill_{row_id}.pdf"
                 full_file_path = os.path.join(DATASET_FOLDER, filename)

            if os.path.exists(full_file_path):
                file_path_android = f"dataset/{filename}"
                file_path_web = filename 
            else:
                print(f"   [Warning] PDF not found: {filename}")
                file_path_android = ""
                file_path_web = ""

            summary = "Summary not available."

            # SQLite Insert (Safe TEXT ID)
            c.execute(f'''
                INSERT INTO bills (bill_id, title, category, status, date_introduced, file_path, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row_id, title, category, status, date_introduced, file_path_android, summary))

            # Firebase Insert
            if db_firestore:
                db_firestore.collection(collection_name).add({
                    "bill_id": row_id,
                    "title": title,
                    "category": category,
                    "status": status,
                    "date_introduced": date_introduced,
                    "file_path": file_path_web,
                    "summary": summary
                })

        elif mode == 'MPS':
            name = row.get('Name', 'Unknown')
            party = row.get('Party', 'Ind')
            constituency = row.get('Constituency', '')
            score = row.get('Performance Score', '0%')

            c.execute(f'''
                INSERT INTO mps (mp_id, name, constituency, party, performance_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (row_id, name, constituency, party, score))

            if db_firestore:
                db_firestore.collection(collection_name).add({
                    "mp_id": row_id,
                    "name": name,
                    "party": party,
                    "constituency": constituency,
                    "performance_score": score
                })

        count += 1
        print(f"Processed: {row.get('Title', row.get('Name', 'Item'))}")

    conn.commit()
    conn.close()
    print("------------------------------------------------")
    print(f"DONE. {count} records uploaded.")

if __name__ == "__main__":
    universal_upload()