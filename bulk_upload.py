import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

def get_absolute_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def bulk_upload():
    """
    Connects to Firebase and performs a bulk upload/update of data from Excel files.
    - Reads data from 'static/dataset/bills.xlsx' and 'static/dataset/mps.xlsx'.
    - Uses 'bill_no' and 'mp_id' as unique keys to update or create documents.
    - Automatically links PDFs from 'static/dataset' if the filename matches the 'bill_no'.
    """
    print("--- Starting Bulk Upload/Update Process ---")

    # --- 1. CONNECT TO FIREBASE ---
    try:
        cred_path = get_absolute_path("serviceAccountKey.json")
        if not os.path.exists(cred_path):
            print(f"❌ ERROR: Firebase credentials not found at {cred_path}")
            print("Please ensure 'serviceAccountKey.json' is in the same directory as the script.")
            return

        cred = credentials.Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase connected successfully.")
    except Exception as e:
        print(f"❌ Firebase connection error: {e}")
        return

    # --- 2. DEFINE FILE PATHS ---
    dataset_path = get_absolute_path("static/dataset")
    bills_file = os.path.join(dataset_path, "bills.xlsx")
    mps_file = os.path.join(dataset_path, "mps.xlsx")

    # --- 3. PROCESS BILLS ---
    print("\n--- Processing Bills ---")
    if os.path.exists(bills_file):
        try:
            df_bills = pd.read_excel(bills_file).astype(str)
            df_bills = df_bills.where(pd.notnull(df_bills), None)
            print(f"Found {len(df_bills)} bills in '{os.path.basename(bills_file)}'. Uploading/Updating...")
            
            for index, row in df_bills.iterrows():
                bill_no = str(row.get('bill_no'))
                if not bill_no or bill_no == 'None':
                    print(f"  ⚠️ Skipping row {index+2} due to missing 'bill_no'.")
                    continue

                bill_data = row.to_dict()
                
                # Check for matching PDF
                pdf_filename = f"{bill_no}.pdf"
                pdf_path = os.path.join(dataset_path, pdf_filename)
                if os.path.exists(pdf_path):
                    bill_data['pdf_url'] = f"/static/dataset/{pdf_filename}"
                    print(f"  🔗 PDF found for bill_no '{bill_no}'.")
                else:
                    bill_data['pdf_url'] = None

                # Use bill_no as the document ID
                doc_ref = db.collection('bills').document(bill_no)
                doc_ref.set(bill_data, merge=True) # merge=True updates fields without overwriting the whole doc
                print(f"  Processed: {bill_data.get('title', 'No Title')} (ID: {bill_no})")
            print("✅ Bills processing complete.")

        except Exception as e:
            print(f"❌ Error processing bills file: {e}")
    else:
        print(f"⚠️ WARNING: Bills file not found at {bills_file}. Skipping bills upload.")

    # --- 4. PROCESS MPs ---
    print("\n--- Processing MPs ---")
    if os.path.exists(mps_file):
        try:
            df_mps = pd.read_excel(mps_file).astype(str)
            df_mps = df_mps.where(pd.notnull(df_mps), None)
            print(f"Found {len(df_mps)} MPs in '{os.path.basename(mps_file)}'. Uploading/Updating...")

            for index, row in df_mps.iterrows():
                mp_id = str(row.get('mp_id'))
                if not mp_id or mp_id == 'None':
                    print(f"  ⚠️ Skipping row {index+2} due to missing 'mp_id'.")
                    continue
                
                mp_data = row.to_dict()

                # Convert numeric fields correctly
                for field in ['attendance_pct', 'questions', 'debates']:
                    if mp_data.get(field) is not None:
                        try:
                            mp_data[field] = float(mp_data[field])
                        except (ValueError, TypeError):
                            mp_data[field] = 0

                # Use mp_id as the document ID
                doc_ref = db.collection('mps').document(mp_id)
                doc_ref.set(mp_data, merge=True)
                print(f"  Processed: {mp_data.get('name', 'No Name')} (ID: {mp_id})")
            print("✅ MPs processing complete.")

        except Exception as e:
            print(f"❌ Error processing MPs file: {e}")
    else:
        print(f"⚠️ WARNING: MPs file not found at {mps_file}. Skipping MPs upload.")

    print("\n--- Bulk Upload/Update Process Finished ---")


if __name__ == "__main__":
    bulk_upload()
    input("\nPress Enter to exit...")

