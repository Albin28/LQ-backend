import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import time
import json

def migrate():
    print("🚀 Starting PDF Cloud Migration...")
    cred_path = "ServiceAccountKey.json"
    cred = credentials.Certificate(cred_path)
    
    with open(cred_path) as f:
        import json
        cert_json = json.load(f)
    project_id = cert_json.get('project_id')
    bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET') or f"{project_id}.appspot.com"

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
    
    db = firestore.client()
    bucket = storage.bucket()
    print(f"✅ Connected to Bucket: {bucket_name}")
    
    bills = db.collection('bills').stream()
    for doc in bills:
        data = doc.to_dict()
        pdf_url = data.get('pdf_url', '')
        
        # If the URL is local (starts with /static/)
        if pdf_url and pdf_url.startswith('/static/dataset/'):
            filename = pdf_url.split('/')[-1]
            local_path = os.path.join('static', 'dataset', filename)
            
            if os.path.exists(local_path):
                print(f"  ⬆️ Migrating {filename}...")
                blob_path = f"bills/{doc.id}/{int(time.time())}_{filename}"
                blob = bucket.blob(blob_path)
                blob.upload_from_filename(local_path, content_type='application/pdf')
                blob.make_public()
                
                # Update Firestore
                db.collection('bills').document(doc.id).update({
                    'pdf_url': blob.public_url,
                    'pdf_blob': blob_path
                })
                print(f"  ✅ Done: {blob.public_url}")
            else:
                print(f"  ⚠️ Local file not found: {local_path}")

    print("🏁 Migration Finished!")

if __name__ == "__main__":
    migrate()
