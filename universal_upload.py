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

# --- HELPER: FIND FILE AUTOMATICALLY ---
def find_excel_file(filename):
    # We check these 3 locations in order
    possible_paths = [
        f"static/dataset/{filename}",  # Best place (Web)
        f"dataset/{filename}",         # Old place
        filename                       # Root folder
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"   [FOUND] Using: {path}")
            return path
            
    return None

# --- 2. UPLOAD BILLS FUNCTION ---
def upload_bills():
    print("\n--- STARTING BILLS UPLOAD ---")
    
    file_path = find_excel_file("bills_metadata.xlsx")
    if not file_path:
        print("❌ Could not find bills_metadata.xlsx")
        return

    df = pd.read_excel(file_path)
    df = df.fillna("") 

    collection_ref = db.collection('bills')

    for index, row in df.iterrows():
        bill_data = {
            'title': row.get('Title', 'Untitled'),
            'category': str(row.get('Category', 'General')).strip(), 
            'date_introduced': str(row.get('Date Introduced', '')).strip(),
            'status': row.get('Status', 'Pending'),
            'summary': row.get('Summary', 'No summary provided.'),
            'file_path': ""
        }

        # PDF Logic (Looks in static/dataset first)
        pdf_name = f"{row.get('Bill ID', 'Unknown')}.pdf"
        if os.path.exists(f"static/dataset/{pdf_name}"):
             bill_data['file_path'] = pdf_name
        elif os.path.exists(f"dataset/{pdf_name}"):
             # If found in old folder, just save the name, but warn user
             bill_data['file_path'] = pdf_name
             print(f"   [NOTE] PDF found in old 'dataset' folder: {pdf_name}")

        doc_id = str(row.get('Bill ID', f'bill_{index}'))
        collection_ref.document(doc_id).set(bill_data)
    
    print("✅ Bills Upload Complete.")

# --- 3. UPLOAD MPs FUNCTION ---
def upload_mps():
    print("\n--- STARTING MP DATA UPLOAD ---")
    
    file_path = find_excel_file("mps_metadata.xlsx")
    if not file_path:
        print("❌ Could not find mps_metadata.xlsx")
        return

    df = pd.read_excel(file_path)
    df = df.fillna(0)

    mps_ref = db.collection('mps')

    for index, row in df.iterrows():
        # 1. Calculate Attendance %
        days_attended = float(row.get('Days_Attended', 0))
        total_days = float(row.get('Total_Days', 1))
        attendance_pct = round((days_attended / total_days) * 100, 1)

        # 2. Capitalize Text
        state = str(row.get('State', 'Unknown')).title()
        house = str(row.get('House', 'Lok Sabha')).title()
        
        mp_data = {
            'name': row.get('MP_Name', 'Unknown MP'),
            'state': state,
            'house': house,
            'constituency': row.get('Constituency', 'N/A'),
            'session': row.get('Session_Name', 'General'),
            'days_attended': int(days_attended),
            'total_days': int(total_days),
            'attendance_pct': attendance_pct,
            'questions': int(row.get('Questions', 0)),
            'debates': int(row.get('Debates', 0))
        }

        # Unique ID: Name + Session (e.g., Amit_Shah_Winter-2024)
        doc_id = f"{mp_data['name']}_{mp_data['session']}".replace(" ", "_")
        mps_ref.document(doc_id).set(mp_data)
        print(f"   [UPLOADED] {mp_data['name']} ({mp_data['session']})")

    print("✅ MP Upload Complete.")

# --- 4. MAIN EXECUTION ---
if __name__ == "__main__":
    upload_bills()
    upload_mps()
    print("\n🎉 ALL SYSTEMS UPDATED.")