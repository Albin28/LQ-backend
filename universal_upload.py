import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import os

# --- 1. SETUP FIREBASE ---
# We check both local and cloud paths for the key
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

# --- 2. UPLOAD BILLS FUNCTION (The Original Engine) ---
def upload_bills():
    print("\n--- STARTING BILLS UPLOAD ---")
    
    # Path to Excel (Checks root, then dataset folder)
    file_path = "bills_metadata.xlsx"
    if not os.path.exists(file_path):
        file_path = "dataset/bills_metadata.xlsx"
        
    if not os.path.exists(file_path):
        print("❌ Could not find bills_metadata.xlsx")
        return

    df = pd.read_excel(file_path)
    df = df.fillna("") # Fill empty cells to prevent errors

    collection_ref = db.collection('bills')

    for index, row in df.iterrows():
        # Excel Column Mapping
        bill_data = {
            'title': row.get('Title', 'Untitled'),
            'category': str(row.get('Category', 'General')).strip(), 
            'date_introduced': str(row.get('Date Introduced', '')).strip(),
            'status': row.get('Status', 'Pending'),
            'summary': row.get('Summary', 'No summary provided.'),
            'file_path': "" # Default to empty
        }

        # PDF Link Logic (Strict Matching)
        # We look in static/dataset first, then dataset
        pdf_name = f"{row.get('Bill ID', 'Unknown')}.pdf"
        
        # Check static/dataset (Web Server standard)
        if os.path.exists(f"static/dataset/{pdf_name}"):
             bill_data['file_path'] = pdf_name
             print(f"   [LINKED] {pdf_name}")
        # Check dataset (Local standard)
        elif os.path.exists(f"dataset/{pdf_name}"):
             bill_data['file_path'] = pdf_name
             print(f"   [LINKED] {pdf_name}")
        else:
             print(f"   [Warning] PDF missing for: {pdf_name}")

        # Upload to Firebase
        # We use the Bill ID as the document ID so we don't get duplicates
        doc_id = str(row.get('Bill ID', f'bill_{index}'))
        collection_ref.document(doc_id).set(bill_data)
    
    print("✅ Bills Upload Complete.")


# --- 3. UPLOAD MPs FUNCTION (The New Engine) ---
def upload_mps():
    print("\n--- STARTING MP DATA UPLOAD ---")
    
    # Path to MP Excel (Looking inside dataset folder as you requested)
    file_path = "dataset/mps_metadata.xlsx"
    
    # Safety Check: If not in dataset, check root
    if not os.path.exists(file_path):
        file_path = "mps_metadata.xlsx"

    if not os.path.exists(file_path):
        print("❌ Could not find mps_metadata.xlsx. Skipping MPs.")
        return

    df = pd.read_excel(file_path)
    df = df.fillna(0) # Fill numbers with 0, text with ""

    mps_ref = db.collection('mps')

    for index, row in df.iterrows():
        # 1. Calculate Attendance % (Auto-Math)
        days_attended = float(row.get('Days_Attended', 0))
        total_days = float(row.get('Total_Days', 1)) # Avoid division by zero
        attendance_pct = round((days_attended / total_days) * 100, 1)

        # 2. Capitalize Text (Auto-Fix for "gujarat" -> "Gujarat")
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

        # 3. Create a Unique ID (Name + Session)
        # This allows "Amit Shah" to have 2 entries (one for Winter, one for Budget)
        doc_id = f"{mp_data['name']}_{mp_data['session']}".replace(" ", "_")
        
        mps_ref.document(doc_id).set(mp_data)
        print(f"   [UPLOADED] {mp_data['name']} ({mp_data['session']})")

    print("✅ MP Upload Complete.")


# --- 4. MAIN EXECUTION ---
if __name__ == "__main__":
    upload_bills() # Run Engine 1
    upload_mps()   # Run Engine 2
    print("\n🎉 ALL SYSTEMS UPDATED SUCCESSFULLY.")