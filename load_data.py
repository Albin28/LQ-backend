import firebase_admin
from firebase_admin import credentials, firestore

# 1. CONNECT
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. THE DATA (Now including Bills!)
bills_data = [
    {
        "title": "The Digital Personal Data Protection Bill",
        "status": "Passed",
        "date": "2023-08-09",
        "text": "The Bill provides for the processing of digital personal data in a manner that recognizes both the right of individuals to protect their personal data and the need to process such personal data for lawful purposes. It establishes a Data Protection Board of India. Significant penalties are proposed for data breaches. It requires consent for data processing and provides certain rights to data principals."
    },
    {
        "title": "The Women's Reservation Bill",
        "status": "Passed",
        "date": "2023-09-20",
        "text": "This Constitution Amendment Bill seeks to reserve one-third of all seats for women in the Lok Sabha and the State Legislative Assemblies. The reservation will be effective after the publication of the census conducted following the commencement of this Act. The reservation will be for a period of 15 years. Rotation of seats reserved for women will be governed by parliamentary law."
    }
]

def upload_bills():
    print("--- 🚀 Uploading Bills ---")
    for bill in bills_data:
        # Use title as ID
        db.collection("bills").document(bill['title']).set(bill)
        print(f"✅ Uploaded: {bill['title']}")

if __name__ == "__main__":
    upload_bills()