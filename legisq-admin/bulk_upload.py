import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import sys
import time
import json

def get_absolute_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def bulk_upload():
    print("--- Starting Bulk Upload/Update Process (Cloud Storage Mode) ---")

    try:
        cred_path = get_absolute_path("ServiceAccountKey.json")
        cred = credentials.Certificate(cred_path)
        
        # Load bucket name from ServiceAccountKey or Env
        with open(cred_path) as f:
            cert_json = json.load(f)
        project_id = cert_json.get('project_id')
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET') or f"{project_id}.appspot.com"

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
        
        db = firestore.client()
        bucket = storage.bucket()
        print(f"✅ Firebase (Admin) connected. Bucket: {bucket_name}")
    except Exception as e:
        print(f"❌ Firebase connection error: {e}")
        return

    dataset_path = get_absolute_path("static/dataset")
    bills_file = os.path.join(dataset_path, "bills.xlsx")
    mps_file = os.path.join(dataset_path, "mps.xlsx")

    # --- PROCESS BILLS ---
    print("\n--- Processing Bills ---")
    if os.path.exists(bills_file):
        try:
            df_bills = pd.read_excel(bills_file).astype(str)
            df_bills = df_bills.where(pd.notnull(df_bills), None)
            
            # Make column names case-insensitive for easier mapping
            df_bills.columns = [c.lower().strip() for c in df_bills.columns]
            print(f"  📂 Found columns: {list(df_bills.columns)}")

            for index, row in df_bills.iterrows():
                # Try common names for the ID column
                bill_no = None
                for col in ['bill_no', 'bill no', 'id', 'billid']:
                    if col in row:
                        val = str(row[col]).strip()
                        if val and val != 'None' and val != 'nan':
                            bill_no = val
                            break
                
                if not bill_no:
                    print(f"  ⚠️ Skipping row {index}: No bill_no or id column found.")
                    continue

                bill_data = row.to_dict()
                
                # Ensure date_introduced exists for Firestore ordering
                if 'date_introduced' not in bill_data or str(bill_data['date_introduced']) in ['None', 'nan', '']:
                    bill_data['date_introduced'] = firestore.SERVER_TIMESTAMP
                
                # Basic cleanup
                bill_data['title'] = bill_data.get('title', bill_data.get('bill_title', 'Unknown Title')).strip()
                bill_data['status'] = bill_data.get('status', 'Introduced').strip()

                print(f"  🔄 Processing Bill ID: {bill_no} - {bill_data['title'][:30]}...")
                pdf_filename = f"{bill_no}.pdf"
                pdf_path = os.path.join(dataset_path, pdf_filename)
                
                if os.path.exists(pdf_path):
                    print(f"  ⬆️ Uploading PDF for bill {bill_no} to Cloud...")
                    blob_path = f"bills/{bill_no}/{int(time.time())}_{pdf_filename}"
                    blob = bucket.blob(blob_path)
                    blob.upload_from_filename(pdf_path, content_type='application/pdf')
                    blob.make_public()
                    bill_data['pdf_url'] = blob.public_url
                    print(f"  🔗 Linked to Cloud URL: {blob.public_url}")
                else:
                    # Keep existing URL if it exists in DB, otherwise None
                    doc = db.collection('bills').document(bill_no).get()
                    if doc.exists:
                        existing = doc.to_dict()
                        bill_data['pdf_url'] = existing.get('pdf_url')

                db.collection('bills').document(bill_no).set(bill_data, merge=True)
                print(f"  ✅ Processed: {bill_data.get('title')} (ID: {bill_no})")
        except Exception as e:
            print(f"❌ Error processing bills: {e}")

    # --- PROCESS MPs ---
    print("\n--- Processing MPs ---")
    if os.path.exists(mps_file):
        try:
            df_mps = pd.read_excel(mps_file).astype(str)
            for index, row in df_mps.iterrows():
                mp_id = str(row.get('mp_id'))
                if not mp_id or mp_id == 'None': continue
                mp_data = row.to_dict()
                for field in ['attendance_pct', 'questions', 'debates']:
                    try: mp_data[field] = float(mp_data[field])
                    except: mp_data[field] = 0
                db.collection('mps').document(mp_id).set(mp_data, merge=True)
                print(f"  ✅ Processed MP: {mp_data.get('name')} (ID: {mp_id})")
        except Exception as e:
            print(f"❌ Error processing MPs: {e}")

    print("\n--- Bulk Upload Finished ---")

import json # Ensure json is imported
if __name__ == "__main__":
    bulk_upload()
    input("\nPress Enter to exit...")
