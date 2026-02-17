import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import time

# Database paths
DATASET_DIR = "static/dataset"
os.makedirs(DATASET_DIR, exist_ok=True)
METADATA_FILE = os.path.join(DATASET_DIR, "bills_metadata.csv")

BASE_URL = "https://prsindia.org"
TRACK_URL = "https://prsindia.org/billtrack"

def sanitize_filename(text):
    clean = re.sub(r'[^\w\s-]', '', text).strip()
    return re.sub(r'[-\s]+', '_', clean)

def fetch_bills():
    print(f"📡 Connecting to {TRACK_URL}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(TRACK_URL, headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to fetch page. Status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Strategy: Find all links to bills
    # Bill links usually start with /billtrack/ and are not system links
    # We filter for links that look like bill slugs (exclude known system paths if any)
    
    potential_links = []
    seen_urls = set()
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Normalize
        if not href.startswith('http'):
            if href.startswith('/'):
                href = BASE_URL + href
            else:
                continue # Skip relative without slash or other protocols

        # Filter criteria
        if '/billtrack/' in href:
            # Exclude non-bill pages if possible
            # Common non-bill paths in billtrack:
            # - ?page=
            # - #
            # - /billtrack (itself)
            if href == TRACK_URL or '?' in href or '#' in href:
                continue
            
            if href not in seen_urls:
                seen_urls.add(href)
                # Use text length as a heuristic? Bill titles are usually long.
                text = a.get_text(strip=True)
                if len(text) > 10: 
                    potential_links.append({"url": href, "title": text})

    print(f"🔍 Found {len(potential_links)} potential bill links.")
    
    bills_data = []
    MAX_BILLS = 15
    count = 0
    
    for link_obj in potential_links:
        if count >= MAX_BILLS: break
        
        url = link_obj['url']
        list_title = link_obj['title']
        
        # Filter: Title must look like a bill
        if not any(x in list_title.lower() for x in ['bill', 'code', 'act', 'vidheyak', 'sanhita', 'ordinance']):
            continue

        print(f"   PLEASE WAIT: Processing '{list_title[:30]}...'")
        
        try:
            det_resp = requests.get(url, headers=headers)
            if det_resp.status_code != 200: continue
            
            det_soup = BeautifulSoup(det_resp.content, 'html.parser')
            
            # 1. Extract Title (h1 often has it)
            h1 = det_soup.find('h1')
            title = h1.get_text(strip=True) if h1 else list_title
            
            # 2. Extract Category (Breadcrumbs)
            category = "General"
            # Try to find breadcrumb text
            # Usually: Home / Bills & Acts / [Category] / ...
            # Let's look for known categories in text if breadcrumb structure is hard
            known_cats = ["Social", "Finance", "Labour", "Health", "Education", "Strategic", "Environment", "Infrastructure", "Legal"]
            text_content = det_soup.get_text(" ", strip=True)
            for cat in known_cats:
                if cat in text_content[:500]: # Check top of page
                    category = cat
                    break
            
            # 3. Extract Status & Date
            status = "Pending"
            # Simple keyword search in text content
            if "Passed by both Houses" in text_content: status = "Passed"
            elif "Assented" in text_content: status = "Act"
            elif "Withdrawn" in text_content: status = "Withdrawn"
            elif "Passed" in text_content: status = "Passed" # Fallback
            
            # Date (Look for "Introduced ... [Date]")
            date_intro = ""
            # Regex to capture: "Introduced" ... (Date like "Dec 18, 2023")
            date_match = re.search(r'Introduced.*?\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})', text_content, re.IGNORECASE)
            if date_match:
                date_intro = date_match.group(1) # Capture just the date part
            else:
                 # Try finding just a date in the "Introduced" row if it exists as a table
                 # But text search is safer fallback
                 pass

            # 4. Find PDF
            pdf_filename = ""
            pdf_link = None
            
            target_texts = ['Bill Text', 'Text of the Bill', 'As Introduced', 'As Passed', 'Ordinance Text']
            for t in target_texts:
                pdf_link = det_soup.find('a', string=re.compile(t, re.IGNORECASE))
                if pdf_link: break
            
            if not pdf_link:
                all_links = det_soup.find_all('a', href=True)
                for a in all_links:
                    if a['href'].lower().endswith('.pdf') and ('bill' in a.get_text().lower() or 'text' in a.get_text().lower()):
                        pdf_link = a
                        break
            
            if pdf_link:
                pdf_url = pdf_link['href']
                if not pdf_url.startswith('http'):
                    pdf_url = BASE_URL + pdf_url
                
                clean_name = sanitize_filename(title) + ".pdf"
                save_path = os.path.join(DATASET_DIR, clean_name)
                
                try:
                    with requests.get(pdf_url, stream=True) as r:
                         r.raise_for_status()
                         with open(save_path, 'wb') as f:
                             for chunk in r.iter_content(chunk_size=8192):
                                 f.write(chunk)
                    pdf_filename = clean_name
                    print(f"      ✅ PDF Saved")
                except Exception as e:
                    print(f"      ⚠️ PDF Download Error: {e}")
            else:
                print("      ⚠️ No PDF found")

            # Add entry
            bills_data.append({
                "Bill_id": f"Bill_{sanitize_filename(title)[:50]}",
                "Title": title,
                "Date Introduced": date_intro,
                "Category": category,
                "Status": status,
                "Summary": f"Official bill regarding {title}.",
                "file_path": pdf_filename
            })
            count += 1
            
        except Exception as e:
            print(f"      ❌ Error parsing detail: {e}")

    # Save
    if bills_data:
        df = pd.DataFrame(bills_data)
        df.to_csv(METADATA_FILE, index=False)
        print(f"\n🎉 Saved {len(bills_data)} bills to {METADATA_FILE}")
    else:
        print("\n⚠️ No bill data extracted.")

def run():
    fetch_bills()

if __name__ == "__main__":
    run()

