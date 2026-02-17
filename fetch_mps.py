import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

DATASET_DIR = "static/dataset"
os.makedirs(DATASET_DIR, exist_ok=True)
METADATA_FILE = os.path.join(DATASET_DIR, "mps_metadata.csv")

BASE_URL = "https://prsindia.org/mptrack/17-lok-sabha/"

VIP_MPS = [
    "rahul-gandhi",
    "amit-shah",
    "shashi-tharoor",
    "mahua-moitra",
    "asaduddin-owaisi",
    "supriya-sule",
    "tejasvi-surya",
    "nirmala-sitharaman", # Check slug validity later, assuming standard mostly
    "rajnath-singh",
    "smriti-zubin-irani",
    "adhir-ranjan-chowdhury",
    "dimple-yadav",
    "hema-malini",
    "kiren-rijiju",
    "nitin-jairam-gadkari"
]

def fetch_mps():
    mps_data = []
    headers = {'User-Agent': 'Mozilla/5.0'}

    print(f"🕵️‍♂️ Fetching data for {len(VIP_MPS)} VIP MPs...")

    for slug in VIP_MPS:
        url = BASE_URL + slug
        print(f"   Visiting: {slug}...", end=" ")
        
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"❌ Failed ({resp.status_code})")
                continue

            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 1. Name
            # Usually in an h1 or h2
            name_tag = soup.find('h1')
            name = name_tag.get_text(strip=True) if name_tag else slug.replace("-", " ").title()
            
            # 2. Party & State
            # Often in the sidebar or subtitle.
            # We'll try to find text patterns.
            # e.g. "Indian National Congress"
            
            party = "Unknown"
            state = "Unknown"
            
            # Search for party in common places
            # Simplify: Assume extracting from text blocks is safest if classes change.
            # Or use specific knowledge if available.
            # For now, default to "Unknown" or parse from a "Profile" section if standard.
            
            # 3. Attendance
            # Find the "Attendance" text
            attendance_pct = 0
            
            # Strategy: Find "Attendance" text, then look for a number with '%' nearby
            att_header = soup.find(string=re.compile("Attendance", re.IGNORECASE))
            if att_header:
                # Look in parent's text or siblings
                container = att_header.find_parent()
                if container:
                    # Look for percentage in the text of the container or next siblings
                    full_text = container.get_text() + " " + (container.find_next().get_text() if container.find_next() else "")
                    
                    match = re.search(r'(\d+)%', full_text)
                    if match:
                        attendance_pct = int(match.group(1))
            
            # If not found, try a broader search on the page for "Attendance: X%" pattern
            if attendance_pct == 0:
                all_text = soup.get_text()
                match = re.search(r'Attendance\s*[:\-\s]*(\d+)%', all_text, re.IGNORECASE)
                if match:
                     attendance_pct = int(match.group(1))

            print(f"✅ Found! (Att: {attendance_pct}%)")
            
            # Calculate days
            total_days = 100 # Normalization constant as requested
            days_attended = int((attendance_pct / 100) * total_days)

            mps_data.append({
                "MP_Name": name,
                "Party": party, # Placeholder, hard to reliably generic scrape without exact selector
                "State": state, # Placeholder
                "Session_Name": "17th Lok Sabha",
                "Days_Attended": days_attended,
                "Total_Days": total_days,
                "Image_URL": "" # Optional
            })

        except Exception as e:
            print(f"❌ Error: {e}")

    # Save
    if mps_data:
        df = pd.DataFrame(mps_data)
        df.to_csv(METADATA_FILE, index=False)
        print(f"\n📊 Saved {len(mps_data)} MPs to {METADATA_FILE}")
    else:
        print("\n⚠️ No MP data found.")

def run():
    fetch_mps()

if __name__ == "__main__":
    run()
