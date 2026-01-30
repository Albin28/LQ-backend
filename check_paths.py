import firebase_admin
from firebase_admin import credentials, firestore
import os

if os.path.exists("serviceAccountKey.json"):
    cred = credentials.Certificate("serviceAccountKey.json")
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass
    db = firestore.client()
    
    docs = db.collection('bills').stream()
    print("--- BILLS FILE PATHS ---")
    for doc in docs:
        d = doc.to_dict()
        print(f"ID: {doc.id} | File Path: '{d.get('file_path')}'")
else:
    print("No key found")
