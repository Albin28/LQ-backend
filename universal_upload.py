import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
import os
import re

# ==========================================
# 1. SETUP FIREBASE
# ==========================================
if os.path.exists("serviceAccountKey.json"):
    cred = credentials.Certificate("serviceAccountKey.json")
elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
    cred = credentials.Certificate("/etc/secrets/serviceAccountKey.json")
else:
    print("❌ Error: serviceAccountKey.json not found!")
    exit()

try:
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'legis-40c06.appspot.com'
    })
    db = firestore.client()
    bucket = storage.bucket()
    print("✅ Connected to Firebase & Storage")
except ValueError:
    print("⚠️ Firebase app already initialized")
    db = firestore.client()
    bucket = storage.bucket()


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def find_data_file(filename):
    """
    Locates the data file (Excel or CSV) in common paths.
    """
    base_name = filename.split('.')[0]
    possible_paths = [
        filename,
        f"static/dataset/{filename}",
        f"dataset/{filename}",
        f"{base_name}.csv",
        f"static/dataset/{base_name}.csv"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"   📂 Found Data File: {path}")
            return path
    return None

def find_pdf_on_disk(directory, bill_id):
    """
    Finds the PDF for a bill (case-insensitive search).
    Input: "Bill_101" -> Finds: "Bill_101.pdf", "bill_101.pdf", OR "Bill 101.pdf" (spaces)
    """
    if not os.path.exists(directory):
        return ""
    
    target_name = f"{bill_id}.pdf"
    all_files = os.listdir(directory)
    
    for f in all_files:
        # Match 1: Exact case-insensitive match (e.g., Bill_101.pdf == bill_101.pdf)
        if f.lower() == target_name.lower():
            return f
        # Match 2: Normalize spaces->underscores in the filename before comparing
        # This catches "Bill 101.pdf" matching against target "Bill_101.pdf"
        if f.lower().replace(" ", "_") == target_name.lower():
            return f
    return ""

def get_col(row, aliases, default=''):
    """
    Robustly gets a value from a row using multiple possible column names.
    """
    # Normalize row keys to lowercase for matching
    row_lower = {k.lower().strip(): v for k, v in row.items()}
    
    for alias in aliases:
        if alias.lower() in row_lower:
            val = row_lower[alias.lower()]
            if pd.isna(val) or str(val).strip() == "":
                return default
            return val
    return default

def sanitize_id(raw_id):
    """
    SAFETY: Converts 'Bill 12/2024' -> 'Bill_12-2024'
    Prevents URL crashes and filesystem errors.
    """
    if pd.isna(raw_id): return "unknown_id"
    # Replace slashes and spaces with dashes/underscores
    safe_id = str(raw_id).strip().replace("/", "-").replace("\\", "-").replace(" ", "_")
    # Remove any other special characters (keep alphanumeric, -, _)
    return re.sub(r'[^a-zA-Z0-9_\-]', '', safe_id)

def clean_date(raw_date):
    """
    Ensures dates are YYYY-MM-DD for correct sorting.
    """
    if pd.isna(raw_date) or str(raw_date).strip() == "":
        return ""
    try:
        return pd.to_datetime(raw_date).strftime('%Y-%m-%d')
    except:
        return str(raw_date)

# ==========================================
# 3. UPLOAD ENGINES
# ==========================================

from urllib.parse import quote

def upload_pdf_to_storage(local_path, filename):
    """
    Uploads a local PDF file to Firebase Storage and returns the public download URL.
    """
    try:
        blob = bucket.blob(f"bills/{filename}")
        blob.upload_from_filename(local_path)
        blob.make_public()
        print(f"   ☁️ Uploaded to Storage: bills/{filename}")
        return blob.public_url
    except Exception as e:
        print(f"   ❌ Storage Upload Error: {e}")
        # Fallback to Firebase Storage URL format if make_public fails (common with strict IAM rules)
        safe_name = quote(f"bills/{filename}", safe="")
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{safe_name}?alt=media"

def upload_bills():
    print("\n--- 🚀 1. BILLS UPLOAD (Safe Mode) ---")
    file_path = find_data_file("bills_metadata.xlsx")
    if not file_path: 
        print("❌ Missing bills_metadata file")
        return

    # Load Data
    if file_path.endswith('.csv'): df = pd.read_csv(file_path)
    else: df = pd.read_excel(file_path)
    
    dataset_folder = "static/dataset"
    count_added = 0
    count_skipped = 0

    for index, row in df.iterrows():
        # 1. GET & SANITIZE ID
        raw_val = get_col(row, ['Bill_id', 'Bill ID', 'ID'], f'bill_{index}')
        clean_id = sanitize_id(raw_val)

        # 2. CHECK EXISTENCE (Preserve Admin Edits)
        doc_ref = db.collection('bills').document(clean_id)
        # CHANGED: We now UPDATE instead of SKIP to allow Excel edits
        is_update = doc_ref.get().exists

        # 3. PREPARE NEW DATA
        clean_date_val = clean_date(get_col(row, ['Date Introduced', 'Date', 'Date_Introduced']))
        # Try to use the file path from CSV first
        csv_file_val = get_col(row, ['file_path', 'PDF', 'File'], '')
        real_filename = ""
        local_pdf_path = ""
        
        if csv_file_val and os.path.exists(os.path.join(dataset_folder, csv_file_val)):
             real_filename = csv_file_val
             local_pdf_path = os.path.join(dataset_folder, csv_file_val)
        else:
             real_filename = find_pdf_on_disk(dataset_folder, clean_id)
             if real_filename:
                 local_pdf_path = os.path.join(dataset_folder, real_filename)

        final_file_url = ""
        if local_pdf_path:
            print(f"   🔹 MATCH: ID '{clean_id}' -> PDF '{real_filename}'")
            # Upload to Firebase Storage!
            final_file_url = upload_pdf_to_storage(local_pdf_path, real_filename)
        else:
            print(f"   🔸 MISSING PDF: For ID '{clean_id}'")
            # See if we already had a file path in DB
            if is_update:
                existing_doc = doc_ref.get().to_dict()
                final_file_url = existing_doc.get('file_path', '')

        bill_data = {
            'title': get_col(row, ['Title', 'Bill Title']),
            'category': str(get_col(row, ['Category', 'Type'], 'General')).strip(),
            'date_introduced': clean_date_val,
            'status': get_col(row, ['Status'], 'Pending'), # Initial status only
            'house': get_col(row, ['House'], 'Lok Sabha'), # Extracted from the user's Excel sheet
            'summary': get_col(row, ['Summary', 'Description'], ''),
            'file_path': final_file_url
        }
        
        doc_ref.set(bill_data, merge=True)
        if is_update:
            print(f"   🔄 UPDATED: {clean_id}")
        else:
            print(f"   ✅ ADDED: {clean_id}")
        count_added += 1
    
    print(f"📊 Bills Report: {count_added} Processed.")


def upload_mps():
    print("\n--- 🚀 2. MP UPLOAD (Safe Mode) ---")
    file_path = find_data_file("mps_metadata.xlsx")
    if not file_path: return

    if file_path.endswith('.csv'): df = pd.read_csv(file_path)
    else: df = pd.read_excel(file_path)

    count_added = 0
    count_skipped = 0

    for index, row in df.iterrows():
        name = get_col(row, ['MP_Name', 'Name', 'MP'])
        session = get_col(row, ['Session_Name', 'Session'], 'General')
        
        # ID Construction
        doc_id = sanitize_id(f"{name}_{session}")
        
        # Check Existence
        doc_ref = db.collection('mps').document(doc_id)
        is_update = doc_ref.get().exists

        # Calculations
        days_attended = float(get_col(row, ['Days_Attended', 'Attended'], 0))
        total_days = float(get_col(row, ['Total_Days', 'Total'], 1))
        attendance_pct = round((days_attended / total_days) * 100, 1) if total_days > 0 else 0

        mp_data = {
            'name': name,
            'state': str(get_col(row, ['State'], 'Unknown')).title(),
            'house': str(get_col(row, ['House'], 'Lok Sabha')).title(),
            'constituency': get_col(row, ['Constituency'], 'N/A'),
            'session': session,
            'days_attended': int(days_attended),
            'total_days': int(total_days),
            'attendance_pct': attendance_pct,
            'questions': int(get_col(row, ['Questions'], 0)),
            'debates': int(get_col(row, ['Debates'], 0))
        }
        
        doc_ref.set(mp_data, merge=True)
        if is_update:
             print(f"   🔄 UPDATED: {doc_id}")
        else:
             print(f"   ✅ ADDED: {doc_id}")
        count_added += 1

    print(f"📊 MPs Report: {count_added} Added, {count_skipped} Skipped.")


def upload_ca():
    print("\n--- 🚀 3. CURRENT AFFAIRS UPLOAD (Safe Mode) ---")
    file_path = find_data_file("current_affairs.xlsx")
    if not file_path: return

    if file_path.endswith('.csv'): df = pd.read_csv(file_path)
    else: df = pd.read_excel(file_path)

    count_added = 0
    count_skipped = 0

    for index, row in df.iterrows():
        clean_id = sanitize_id(get_col(row, ['CA_ID', 'ID'], f'ca_{index}'))
        
        # Check Existence
        doc_ref = db.collection('current_affairs').document(clean_id)
        is_update = doc_ref.get().exists

        ca_data = {
            'date': clean_date(get_col(row, ['Date', 'Published'])),
            'headline': get_col(row, ['Headline', 'Title'], 'Untitled'),
            'link': get_col(row, ['Link', 'URL'], '#'),
            'summary': get_col(row, ['Summary'], '')
        }
        
        doc_ref.set(ca_data, merge=True)
        if is_update:
             print(f"   🔄 UPDATED: {clean_id}")
        else:
             print(f"   ✅ ADDED: {clean_id}")
        count_added += 1

    print(f"📊 News Report: {count_added} Added, {count_skipped} Skipped.")

# ==========================================
# 4. EXECUTION
# ==========================================
if __name__ == "__main__":
    upload_bills()
    upload_mps()
    upload_ca()
    print("\n🎉 ALL SYSTEMS SYNCED (Admin Data Preserved).")