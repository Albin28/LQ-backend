import firebase_admin
from firebase_admin import credentials, firestore
import os
import shutil

# 1. SETUP FIREBASE
if os.path.exists("serviceAccountKey.json"):
    cred = credentials.Certificate("serviceAccountKey.json")
else:
    # Try env var or other paths if needed, but for local dev this is usually enough
    # If running on Vercel, this script might not work directly without env vars, 
    # but the user context implies local execution capability or direct DB access.
    # We will assume serviceAccountKey.json is present as seen in file list.
    print("❌ serviceAccountKey.json not found. Make sure it is in the root directory.")
    exit()

try:
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Connected to Firebase")
except ValueError:
    print("⚠️ Firebase app already initialized")
    db = firestore.client()

# 2. CLEAN DATABASE
def delete_collection(coll_ref, batch_size=10):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f'   Deleting doc {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

print("\n🗑️ Clearing existing data...")
delete_collection(db.collection('bills'))
delete_collection(db.collection('mps'))
print("✅ Database cleared.")

# 3. GENERATE DUMMY PDFs
DATASET_DIR = "static/dataset"
if not os.path.exists(DATASET_DIR):
    os.makedirs(DATASET_DIR)

print("\n📄 Generating dummy PDF files...")
pdf_files = []
for i in range(1, 6):
    filename = f"bill_sample_{i}.pdf"
    filepath = os.path.join(DATASET_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(f"This is a dummy content for Bill {i}.")
    pdf_files.append(filename)
    print(f"   Created {filename}")

# 4. SEED BILLS
print("\n📜 Seeding Bills...")
bills_data = [
    {
        "id": "bill_001",
        "title": "The Digital Education Transformation Bill, 2025",
        "category": "Education",
        "date_introduced": "2025-02-10",
        "status": "In Discussion",
        "summary": "Aims to integrate AI and digital tools in primary education across all states.",
        "file_path": pdf_files[0]
    },
    {
        "id": "bill_002",
        "title": "Green Agriculture Subsidy Act, 2024",
        "category": "Agriculture",
        "date_introduced": "2024-12-05",
        "status": "Passed",
        "summary": "Provides subsidies for farmers adopting organic and sustainable farming practices.",
        "file_path": pdf_files[1]
    },
    {
        "id": "bill_003",
        "title": "National Cybersecurity Defense Framework",
        "category": "Defence",
        "date_introduced": "2025-01-15",
        "status": "Pending",
        "summary": "Establishes a new command center for national cyber defense operations.",
        "file_path": pdf_files[2]
    },
    {
        "id": "bill_004",
        "title": "Universal Healthcare Access Amendment",
        "category": "Health",
        "date_introduced": "2024-11-20",
        "status": "Drafting",
        "summary": "Expands insurance coverage to include mental health and preventative care.",
        "file_path": pdf_files[3]
    },
    {
        "id": "bill_005",
        "title": "Fintech Innovation and Regulation Bill",
        "category": "Finance",
        "date_introduced": "2025-02-01",
        "status": "Committee Stage",
        "summary": "Regulates usage of blockchain in banking and promotes fintech startups.",
        "file_path": pdf_files[4]
    }
]

for bill in bills_data:
    bill_id = bill.pop("id")
    db.collection('bills').document(bill_id).set(bill)
    print(f"   Created Bill: {bill['title']}")

# 5. SEED MPs
print("\n👤 Seeding MPs...")
mps_data = [
    {
        "id": "mp_001",
        "name": "Amit Sharma",
        "state": "Uttar Pradesh",
        "constituency": "Lucknow",
        "house": "Lok Sabha",
        "session": "Budget Session 2025",
        "days_attended": 45,
        "total_days": 50,
        "attendance_pct": 90.0,
        "questions": 12,
        "debates": 5
    },
    {
        "id": "mp_002",
        "name": "Priya Reddy",
        "state": "Telangana",
        "constituency": "Hyderabad",
        "house": "Lok Sabha",
        "session": "Budget Session 2025",
        "days_attended": 20,
        "total_days": 50,
        "attendance_pct": 40.0,
        "questions": 2,
        "debates": 1
    },
    {
        "id": "mp_003",
        "name": "Rahul Verma",
        "state": "Delhi",
        "constituency": "New Delhi",
        "house": "Rajya Sabha",
        "session": "Winter Session 2024",
        "days_attended": 48,
        "total_days": 50,
        "attendance_pct": 96.0,
        "questions": 25,
        "debates": 10
    },
    {
        "id": "mp_004",
        "name": "Sneha Gupta",
        "state": "Maharashtra",
        "constituency": "Mumbai South",
        "house": "Lok Sabha",
        "session": "Budget Session 2025",
        "days_attended": 35,
        "total_days": 50,
        "attendance_pct": 70.0,
        "questions": 8,
        "debates": 3
    },
    {
        "id": "mp_005",
        "name": "Vikram Singh",
        "state": "Punjab",
        "constituency": "Amritsar",
        "house": "Rajya Sabha",
        "session": "Monsoon Session 2024",
        "days_attended": 42,
        "total_days": 50,
        "attendance_pct": 84.0,
        "questions": 15,
        "debates": 6
    }
]

for mp in mps_data:
    mp_id = mp.pop("id")
    db.collection('mps').document(mp_id).set(mp)
    print(f"   Created MP: {mp['name']}")

print("\n✨ Database Reset & Seeding Complete!")
