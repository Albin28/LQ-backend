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
    "asaduddin-owaisi"
]

def fetch_mps():
    mps_data = []
    headers = {'User-Agent': 'Mozilla/5.0'}

    print(f"🕵️‍♂️ Fetching data for {len(VIP_MPS)} VIP MPs...")

    for slug in VIP_MPS:
        # Note: Slug format for 17th Lok Sabha might vary.
        # Try constructing URL carefully.  The base URL is for 17th Lok Sabha.
        # If the MP was in 17th, it works. If not, it fails.
        url = BASE_URL + slug
        print(f"   Visiting: {slug}...", end=" ")
        
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"❌ Failed ({resp.status_code})")
                continue

            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 1. Name
            name_tag = soup.find('h1')
            name = name_tag.get_text(strip=True) if name_tag else slug.replace("-", " ").title()
            
            # 2. Party & State
            # Often in the sub-header links or text
            # e.g. "Indian National Congress ( 53 more MPs )"
            party = "Unknown"
            state = "Unknown"
            
            text_content = soup.get_text(" ", strip=True)
            
            # Try finding state (List of states is long, but we can guess from context or specific links)
            # PRS usually links the state.
            state_link = soup.find('a', href=lambda h: h and 'state=' in h)
            if state_link:
                state = state_link.get_text(strip=True).split('(')[0].strip()
            
            # Try finding party
            party_link = soup.find('a', href=lambda h: h and 'political_party' in h)
            if party_link:
                party = party_link.get_text(strip=True).split('(')[0].strip()

            # 3. Attendance
            # Look for the block containing "Attendance" and extract the percentage number.
            attendance_pct = 0
            
            # Search for specific div classes if possible, but based on text:
            # "Attendance" is usually followed by a number and "%" in a visual chart or text.
            # Let's search for "Attendance" string, then find the nearest number.
            
            # Finding all strings with "Attendance"
            att_strings = soup.find_all(string=re.compile("Attendance", re.IGNORECASE))
            for s in att_strings:
                # Check parent text for regex
                parent_text = s.find_parent().get_text()
                match = re.search(r'Attendance.*?(\d{1,3})%', parent_text, re.IGNORECASE | re.DOTALL)
                if match:
                    attendance_pct = int(match.group(1))
                    break
                
                # Check siblings
                # sometimes "Attendance" is a label, value is in next div
                # We can try to look at the whole text following this occurrence
                following_text = s.find_parent().find_next().get_text() if s.find_parent().find_next() else ""
                match_sib = re.search(r'^(\d{1,3})%', following_text.strip())
                if match_sib:
                    attendance_pct = int(match_sib.group(1))
                    break
            
            # Fallback: look for just number% near "Attendance" in a larger chunk
            if attendance_pct == 0:
                 match_broad = re.search(r'Attendance\s*[:\-\s]*\n*(\d{1,3})%', text_content, re.IGNORECASE)
                 if match_broad:
                     attendance_pct = int(match_broad.group(1))

            print(f"✅ Found! (Att: {attendance_pct}%)")
            
            # Calculate days
            total_days = 273 # Approx days in 17th LS 
            days_attended = int((attendance_pct / 100) * total_days)

            mps_data.append({
                "MP_Name": name,
                "Party": party, 
                "State": state,
                "Session_Name": "17th Lok Sabha",
                "Days_Attended": days_attended,
                "Total_Days": total_days,
                "Image_URL": "" 
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
