import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import os

# --- 1. SETUP FIREBASE ---
if os.path.exists("serviceAccountKey.json"):
    cred = credentials.Certificate("serviceAccountKey.json")
elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
    cred = credentials.Certificate("/etc/secrets/serviceAccountKey.json")
else:
    print("❌ Error: serviceAccountKey.json not found!")
    exit()

try:
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Connected to Firebase")
except ValueError:
    print("⚠️ Firebase app already initialized")
    db = firestore.client()

# --- HELPER: FIND EXCEL FILE ---
def find_excel_file(filename):
    possible_paths = [f"static/dataset/{filename}", f"dataset/{filename}", filename]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"   [FOUND] Excel: {path}")
            return path
    return None

# --- HELPER: SMART PDF FINDER ---
def find_pdf_on_disk(directory, bill_id):
    """
    Finds the PDF even if case sensitivity is different.
    Input: "Bill_001" -> Finds: "Bill_001.pdf" or "bill_001.pdf"
    """
    if not os.path.exists(directory):
        return ""
    
    target_name = f"{bill_id}.pdf"
    all_files = os.listdir(directory)
    
    for f in all_files:
        if f.lower() == target_name.lower():
            return f  # Return the REAL filename (e.g. "Bill_001.pdf")
            
    return ""

# --- ENGINE 1: BILLS (FIXED!) ---
def upload_bills():
    print("\n--- 1. BILLS UPLOAD ---")
    file_path = find_excel_file("bills_metadata.xlsx")
    if not file_path:
        print("❌ Missing bills_metadata.xlsx")
        return

    df = pd.read_excel(file_path).fillna("")
    batch = db.batch() 
    dataset_folder = "static/dataset"

    for index, row in df.iterrows():
        # --- KEY FIX: USING YOUR EXACT COLUMN NAME "Bill_id" ---
        # We try 'Bill_id' first, then 'Bill ID' just in case.
        raw_id = str(row.get('Bill_id', row.get('Bill ID', f'bill_{index}'))).strip()
        
        # Search for the PDF using the Smart Finder
        real_filename = find_pdf_on_disk(dataset_folder, raw_id)

        if real_filename:
            print(f"   🔹 MATCH: ID '{raw_id}' -> File '{real_filename}'")
        else:
            print(f"   🔸 MISSING: Could not find PDF for ID '{raw_id}'")

        doc_ref = db.collection('bills').document(raw_id)
        
        bill_data = {
            'title': row.get('Title', 'Untitled'),
            'category': str(row.get('Category', 'General')).strip(), 
            'date_introduced': str(row.get('Date Introduced', '')).strip(),
            'status': row.get('Status', 'Pending'),
            'summary': row.get('Summary', 'No summary provided.'),
            'file_path': real_filename 
        }
        batch.set(doc_ref, bill_data)
    
    batch.commit()
    print("✅ Bills Updated.")

# --- ENGINE 2: MPs ---
def upload_mps():
    print("\n--- 2. MP UPLOAD ---")
    file_path = find_excel_file("mps_metadata.xlsx")
    if not file_path: return

    df = pd.read_excel(file_path).fillna(0)
    batch = db.batch()

    for index, row in df.iterrows():
        # Using your exact columns: [Days_Attended], [Total_Days]
        days_attended = float(row.get('Days_Attended', 0))
        total_days = float(row.get('Total_Days', 1))
        attendance_pct = round((days_attended / total_days) * 100, 1) if total_days > 0 else 0

        mp_data = {
            'name': row.get('MP_Name', 'Unknown MP'),
            'state': str(row.get('State', 'Unknown')).title(),
            'house': str(row.get('House', 'Lok Sabha')).title(),
            'constituency': row.get('Constituency', 'N/A'),
            'session': row.get('Session_Name', 'General'),
            'days_attended': int(days_attended),
            'total_days': int(total_days),
            'attendance_pct': attendance_pct,
            'questions': int(row.get('Questions', 0)),
            'debates': int(row.get('Debates', 0))
        }
        doc_id = f"{mp_data['name']}_{mp_data['session']}".replace(" ", "_")
        batch.set(db.collection('mps').document(doc_id), mp_data)

    batch.commit()
    print("✅ MPs Updated.")

# --- ENGINE 3: CURRENT AFFAIRS ---
def upload_ca():
    print("\n--- 3. CURRENT AFFAIRS UPLOAD ---")
    file_path = find_excel_file("current_affairs.xlsx")
    if not file_path: return

    df = pd.read_excel(file_path).fillna("")
    batch = db.batch()

    for index, row in df.iterrows():
        ca_data = {
            'date': str(row.get('Date', '')).strip(),
            'headline': row.get('Headline', 'Untitled'),
            'link': row.get('Link', '#'),
            'summary': row.get('Summary', '')
        }
        # Using your exact column: [CA_ID]
        doc_id = str(row.get('CA_ID', f'ca_{index}'))
        batch.set(db.collection('current_affairs').document(doc_id), ca_data)

    batch.commit()
    print("✅ Current Affairs Updated.")

if __name__ == "__main__":
    upload_bills()
    upload_mps()
    upload_ca()
    print("\n🎉 ALL SYSTEMS UPDATED.")