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
    
    # Try multiple common filenames
    bills_candidates = ["bills.xlsx", "bills_metadata.xlsx", "Bills.xlsx"]
    mps_candidates = ["mps.xlsx", "mps_metadata.xlsx", "MPs.xlsx"]
    
    bills_file = None
    for c in bills_candidates:
        p = os.path.join(dataset_path, c)
        if os.path.exists(p):
            bills_file = p
            break
            
    mps_file = None
    for c in mps_candidates:
        p = os.path.join(dataset_path, c)
        if os.path.exists(p):
            mps_file = p
            break

    # --- PROCESS BILLS ---
    print("\n--- Processing Bills ---")
    if bills_file:
        try:
            print(f"  📖 Reading: {os.path.basename(bills_file)}...")
            df_bills = pd.read_excel(bills_file).astype(str)
            df_bills = df_bills.where(pd.notnull(df_bills), None)
            
            # Make column names case-insensitive for easier mapping
            df_bills.columns = [c.lower().strip() for c in df_bills.columns]
            # print(f"  📂 Found columns: {list(df_bills.columns)}")

            def clean_val(v):
                if v is None: return None
                s = str(v).strip()
                if s.lower() in ['nan', 'none', '']: return None
                return s

            count = 0
            for index, row in df_bills.iterrows():
                # Try common names for the ID column
                bill_no = None
                for col in ['bill_no', 'bill no', 'id', 'billid']:
                    if col in row:
                        val = clean_val(row[col])
                        if val:
                            bill_no = val
                            break
                
                if not bill_no:
                    # Skip rows that are truly empty
                    if not any(clean_val(v) for v in row.values):
                        continue
                    print(f"  ⚠️ Skipping row {index}: No bill_no or id column found.")
                    continue

                # UNIVERSAL CLEAN: Trim and remove 'nan'/'none'
                bill_data = {k: clean_val(v) for k, v in row.to_dict().items()}
                
                # Ensure date_introduced exists for Firestore ordering
                if not bill_data.get('date_introduced'):
                    bill_data['date_introduced'] = firestore.SERVER_TIMESTAMP
                
                # Column mapping cleanup
                bill_data['title'] = bill_data.get('title', bill_data.get('bill_title', 'Unknown Title'))
                bill_data['status'] = bill_data.get('status', 'Introduced')

                # Local PDF Linking
                pdf_filename = f"{bill_no}.pdf"
                pdf_path = os.path.join(dataset_path, pdf_filename)
                
                if os.path.exists(pdf_path):
                    bill_data['pdf_url'] = f"/static/dataset/{pdf_filename}"
                else:
                    # Keep existing URL if it exists in DB, otherwise None
                    doc = db.collection('bills').document(bill_no).get()
                    if doc.exists:
                        existing = doc.to_dict()
                        bill_data['pdf_url'] = existing.get('pdf_url')

                db.collection('bills').document(bill_no).set(bill_data, merge=True)
                print(f"  ✅ Processed: {bill_data.get('title')} (ID: {bill_no})")
                count += 1
            print(f"  🎉 Finished processing {count} bills.")
        except Exception as e:
            print(f"❌ Error processing bills: {e}")
    else:
        print(f"  ⚠️ Warning: No bills Excel file found in {dataset_path}")
        print(f"     (Looked for: {', '.join(bills_candidates)})")

    # --- PROCESS MPs ---
    print("\n--- Processing MPs ---")
    if mps_file:
        try:
            print(f"  📖 Reading: {os.path.basename(mps_file)}...")
            df_mps = pd.read_excel(mps_file).astype(str)
            count = 0
            for index, row in df_mps.iterrows():
                # Try common names for MP ID
                mp_id = None
                for col in ['mp_id', 'id', 'mp id']:
                    if col in row:
                        val = clean_val(row[col])
                        if val:
                            mp_id = val
                            break
                
                if not mp_id: continue
                
                # UNIVERSAL CLEAN: Trim and remove 'nan'/'none'
                mp_data = {k: clean_val(v) for k, v in row.to_dict().items()}
                
                for field in ['attendance_pct', 'questions', 'debates']:
                    try: mp_data[field] = float(mp_data[field])
                    except: mp_data[field] = 0
                db.collection('mps').document(mp_id).set(mp_data, merge=True)
                print(f"  ✅ Processed MP: {mp_data.get('name')} (ID: {mp_id})")
                count += 1
            print(f"  🎉 Finished processing {count} MPs.")
        except Exception as e:
            print(f"❌ Error processing MPs: {e}")
    else:
        print(f"  ⚠️ Warning: No MPs Excel file found in {dataset_path}")
        print(f"     (Looked for: {', '.join(mps_candidates)})")

    print("\n--- Bulk Upload Finished ---")

import json # Ensure json is imported
if __name__ == "__main__":
    bulk_upload()
    input("\nPress Enter to exit...")
