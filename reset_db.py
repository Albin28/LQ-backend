import firebase_admin
from firebase_admin import credentials, firestore
import os

if os.path.exists("serviceAccountKey.json"):
    cred = credentials.Certificate("serviceAccountKey.json")
elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
    cred = credentials.Certificate("/etc/secrets/serviceAccountKey.json")
else:
    print("Error: Key not found.")
    exit()

try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

db = firestore.client()

def delete_collection(coll_name):
    docs = db.collection(coll_name).stream()
    for doc in docs:
        print(f"Deleting {doc.id}...")
        doc.reference.delete()
    print(f"✅ Cleared '{coll_name}'.")

delete_collection('bills')
delete_collection('mps')
delete_collection('current_affairs')
print("--- DATABASE RESET COMPLETE ---")