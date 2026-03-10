import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys
import json
import base64
import requests
from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

def get_absolute_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def clean_val(v):
    """Strip whitespace and return None for nan/none/empty values."""
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ['nan', 'none', '']:
        return None
    return s

def bulk_upload():
    print("--- Starting Bulk Upload/Update Process ---")

    try:
        cred_path = get_absolute_path("ServiceAccountKey.json")
        cred = credentials.Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase (Firestore) connected.")
    except Exception as e:
        print(f"❌ Firebase connection error: {e}")
        return

    # --- GitHub storage config ---
    github_token  = os.getenv("GITHUB_TOKEN")
    github_repo   = os.getenv("GITHUB_REPO")
    github_branch = os.getenv("GITHUB_BRANCH", "main")
    if github_token and github_repo:
        print(f"✅ GitHub storage: {github_repo}")
    else:
        print("⚠️  GitHub storage not configured — PDFs skipped (existing urls preserved).")

    def upload_to_github(file_path, bill_id, filename):
        """Upload a local PDF to a public GitHub repo. Returns raw.githubusercontent.com URL."""
        if not github_token or not github_repo:
            raise Exception("GITHUB_TOKEN and GITHUB_REPO must be set in .env")
        path    = f"bills/{bill_id}/{filename}"
        api_url = f"https://api.github.com/repos/{github_repo}/contents/{path}"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept":        "application/vnd.github.v3+json",
        }
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        # Get existing SHA if file already exists (needed for update)
        sha = None
        existing = requests.get(api_url, headers=headers, timeout=15)
        if existing.status_code == 200:
            sha = existing.json().get("sha")
        body = {
            "message": f"Upload PDF for bill {bill_id}",
            "content": base64.b64encode(file_bytes).decode(),
            "branch":  github_branch,
        }
        if sha:
            body["sha"] = sha
        resp = requests.put(api_url, json=body, headers=headers, timeout=60)
        if not resp.ok:
            raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return f"https://raw.githubusercontent.com/{github_repo}/{github_branch}/{path}"

    dataset_path = get_absolute_path("static/dataset")

    # Try multiple common filenames
    bills_candidates = ["bills.xlsx", "bills_metadata.xlsx", "Bills.xlsx"]
    mps_candidates   = ["mps.xlsx",   "mps_metadata.xlsx",   "MPs.xlsx"]

    bills_file = next((os.path.join(dataset_path, c) for c in bills_candidates
                       if os.path.exists(os.path.join(dataset_path, c))), None)
    mps_file   = next((os.path.join(dataset_path, c) for c in mps_candidates
                       if os.path.exists(os.path.join(dataset_path, c))), None)

    # --- PROCESS BILLS ---
    print("\n--- Processing Bills ---")
    if bills_file:
        try:
            print(f"  📖 Reading: {os.path.basename(bills_file)}...")
            df_bills = pd.read_excel(bills_file).astype(str)
            df_bills = df_bills.where(pd.notnull(df_bills), None)
            df_bills.columns = [c.lower().strip() for c in df_bills.columns]

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
                    if not any(clean_val(v) for v in row.values):
                        continue
                    print(f"  ⚠️ Skipping row {index}: No bill_no or id column found.")
                    continue

                bill_data = {k: clean_val(v) for k, v in row.to_dict().items()}

                # Ensure date_introduced exists for Firestore ordering
                if not bill_data.get('date_introduced'):
                    bill_data['date_introduced'] = firestore.SERVER_TIMESTAMP

                bill_data['title']  = bill_data.get('title', bill_data.get('bill_title', 'Unknown Title'))
                bill_data['status'] = bill_data.get('status', 'Introduced')

                # PDF upload
                pdf_filename = f"{bill_no}.pdf"
                pdf_path     = os.path.join(dataset_path, pdf_filename)

                # Preserve existing pdf_url if no local PDF found
                existing_pdf_url = None
                doc = db.collection('bills').document(bill_no).get()
                if doc.exists:
                    existing_pdf_url = doc.to_dict().get('pdf_url')

                if os.path.exists(pdf_path):
                    try:
                        url = upload_to_github(pdf_path, bill_no, pdf_filename)
                        bill_data['pdf_url'] = url
                        print(f"    ⬆️  PDF uploaded to GitHub: {url}")
                    except Exception as pe:
                        print(f"    ⚠️  GitHub upload failed for {pdf_filename}: {pe}")
                        bill_data['pdf_url'] = existing_pdf_url
                else:
                    bill_data['pdf_url'] = existing_pdf_url

                db.collection('bills').document(bill_no).set(bill_data, merge=True)
                print(f"  ✅ Processed: {bill_data.get('title')} (ID: {bill_no})")
                count += 1

            print(f"  🎉 Finished processing {count} bills.")
        except Exception as e:
            print(f"❌ Error processing bills: {e}")
    else:
        print(f"  ⚠️ No bills Excel file found in {dataset_path}")
        print(f"     (Looked for: {', '.join(bills_candidates)})")

    # --- PROCESS MPs ---
    print("\n--- Processing MPs ---")
    if mps_file:
        try:
            print(f"  📖 Reading: {os.path.basename(mps_file)}...")
            df_mps = pd.read_excel(mps_file).astype(str)
            count = 0
            for index, row in df_mps.iterrows():
                mp_id = None
                for col in ['mp_id', 'id', 'mp id']:
                    if col in row:
                        val = clean_val(row[col])
                        if val:
                            mp_id = val
                            break

                if not mp_id:
                    continue

                mp_data = {k: clean_val(v) for k, v in row.to_dict().items()}

                for field in ['attendance_pct', 'questions', 'debates']:
                    try:
                        mp_data[field] = float(mp_data[field])
                    except Exception:
                        mp_data[field] = 0

                db.collection('mps').document(mp_id).set(mp_data, merge=True)
                print(f"  ✅ Processed MP: {mp_data.get('name')} (ID: {mp_id})")
                count += 1

            print(f"  🎉 Finished processing {count} MPs.")
        except Exception as e:
            print(f"❌ Error processing MPs: {e}")
    else:
        print(f"  ⚠️ No MPs Excel file found in {dataset_path}")
        print(f"     (Looked for: {', '.join(mps_candidates)})")

    print("\n--- Bulk Upload Finished ---")

if __name__ == "__main__":
    bulk_upload()
    input("\nPress Enter to exit...")
