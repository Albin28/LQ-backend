import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime

# --- Configuration ---
DB_NAME = "legisq_data.db"
# This points to the new separate folder for data
DATASET_FOLDER = "dataset"
EXCEL_FILE = "bills_metadata.xlsx"  # Make sure this name matches your file in the dataset folder

def init_db():
    """Initializes the database with the correct schema."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Created table without the 'summary' column since we are removing AI for now
    # If you want to keep the column for future use but leave it empty, that's fine too.
    # Here I am keeping it generic so the app doesn't break if it expects the column.
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
    print(f"Database {DB_NAME} initialized.")

def clean_date(date_val):
    """
    Fixes the 'undefined' date issue.
    Converts various date formats into a standard YYYY-MM-DD string.
    """
    if pd.isna(date_val) or date_val == "undefined" or str(date_val).strip() == "":
        return datetime.now().strftime("%Y-%m-%d") # Fallback to today if missing
    
    try:
        # Pandas is very smart at guessing date formats
        return pd.to_datetime(date_val).strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Warning: Could not parse date '{date_val}'. Using today's date.")
        return datetime.now().strftime("%Y-%m-%d")

def bulk_upload():
    """Reads Excel from the dataset folder and populates the DB."""
    
    excel_path = os.path.join(DATASET_FOLDER, EXCEL_FILE)

    if not os.path.exists(excel_path):
        print(f"Error: Could not find {EXCEL_FILE} in the '{DATASET_FOLDER}' folder.")
        print("Please create the 'dataset' folder and move your files there.")
        return

    print("Reading Excel file...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Clear existing data to avoid duplicates (Optional - remove this block if you want to append)
    c.execute('DELETE FROM legislation') 
    print("Cleared existing data.")

    print(f"Processing {len(df)} rows...")

    for index, row in df.iterrows():
        title = row.get('Title', 'Untitled')
        category = row.get('Category', 'General')
        status = row.get('Status', 'Pending')
        
        # 1. Fix the Date Issue
        raw_date = row.get('Date Introduced', '')
        date_introduced = clean_date(raw_date)

        # 2. Handle File Paths relative to the dataset folder
        filename = row.get('Filename', '')
        # We store the path assuming the app will look inside the dataset folder
        # or we just store the filename if the app handles the folder logic.
        # Let's store the full relative path for safety: "dataset/filename.pdf"
        file_path = os.path.join(DATASET_FOLDER, filename) if filename else None

        # 3. NO AI Summary (As requested)
        # We insert a placeholder or empty string
        summary = "Summary not generated."

        c.execute('''
            INSERT INTO legislation (title, category, status, date_introduced, file_path, summary)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, category, status, date_introduced, file_path, summary))

        print(f"Added: {title} | Date: {date_introduced}")

    conn.commit()
    conn.close()
    print("Bulk upload completed successfully!")

if __name__ == "__main__":
    init_db()
    bulk_upload()