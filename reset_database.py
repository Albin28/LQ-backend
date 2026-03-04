import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    db = None
    try:
        # Vercel will use environment variables, local will use the file
        if os.getenv('VERCEL_ENV') == 'production':
            cert_json_str = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
            if not cert_json_str:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set.")
            cert_json = json.loads(cert_json_str)
            cred = credentials.Certificate(cert_json)
            bucket_name = cert_json.get('project_id') + '.appspot.com'
        else:
            # Local development
            cred = credentials.Certificate("serviceAccountKey.json")
            with open("serviceAccountKey.json") as f:
                cert_json = json.load(f)
            bucket_name = cert_json.get('project_id') + '.appspot.com'

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
        
        db = firestore.client()
        print("✅ Firebase connected successfully.")
        return db
    except Exception as e:
        print(f"❌ Firebase connection error: {e}")
        return None

def delete_collection(coll_ref, batch_size):
    """Deletes a collection in batches."""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f"Deleting doc {doc.id}...")
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

def main():
    """Main function to reset the database."""
    db = initialize_firebase()
    if not db:
        print("Database reset failed. Could not connect to Firebase.")
        return

    collections_to_delete = ['bills', 'mps']
    
    for collection_name in collections_to_delete:
        print(f"\n--- Deleting collection: {collection_name} ---")
        coll_ref = db.collection(collection_name)
        delete_collection(coll_ref, 50)
        print(f"✅ Collection '{collection_name}' has been cleared.")

    print("\nDatabase reset complete.")

if __name__ == '__main__':
    main()
