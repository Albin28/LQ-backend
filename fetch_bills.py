import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

# Database paths
DATASET_DIR = "static/dataset"
os.makedirs(DATASET_DIR, exist_ok=True)
METADATA_FILE = os.path.join(DATASET_DIR, "bills_metadata.csv")

BASE_URL = "https://prsindia.org"
TRACK_URL = "https://prsindia.org/billtrack"

def sanitize_filename(text):
    """
    Sanitizes title to be a safe filename.
    e.g., "The Telecommunications Bill, 2023" -> "The_Telecommunications_Bill_2023"
    """
    clean = re.sub(r'[^\w\s-]', '', text).strip()
    return re.sub(r'[-\s]+', '_', clean)

def fetch_bills():
    print(f"📡 Connecting to {TRACK_URL}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(TRACK_URL, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch page. Status: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Locate the bills table (Look for the main table)
    # The structure usually has a table with class 'views-table' or simple table tags
    # We'll take the first table we find that looks like legislative data.
    
    # Try finding the specific view content
    # Based on general PRS structure, tables are often in div.view-content
    
    bills_data = []
    
    # Finding all rows
    # This selector might need adjustment if PRS changes layout, but iterating rows usually works.
    rows = soup.find_all('tr')
    
    count = 0
    MAX_BILLS = 15
    
    print("🔍 Parsing Bills...")
    
    for row in rows:
        if count >= MAX_BILLS: break
        
        cols = row.find_all('td')
        if not cols: continue # Skip header or empty rows
        
        # PRS Bill Track Table Columns (Approximate):
        # Title | Category | Introduced | Status
        
        # We need to be careful about column indices. 
        # Usually: Title (link) is in first or second col.
        
        link_tag = row.find('a')
        if not link_tag: continue
        
        title = link_tag.get_text(strip=True)
        detail_url = BASE_URL + link_tag['href']
        
        # Iterate cols to find date/category/status
        # We will grab all text and guess based on content or position.
        # Assuming standard layout: Title (0), Category (1), Introduced Date (2), House (3), Status (4)
        
        category = "General"
        date_intro = ""
        status = "Pending"
        
        if len(cols) > 2:
            # Try to identify category
            # If col text is short and looks like "Social", "Finance", etc.
            category = cols[1].get_text(strip=True)
            
            # Try to identify date (look for digits and month names)
            date_text = cols[2].get_text(strip=True)
            if re.search(r'\d{4}', date_text):
                date_intro = date_text
            
            # Status
            status_text = cols[-1].get_text(strip=True)
            if status_text:
                status = status_text

        # ---------------------------------------------------------
        # 🟢 DEEP DIVE: VISIT DETAIL PAGE FOR PDF
        # ---------------------------------------------------------
        pdf_filename = ""
        try:
            print(f"   PLEASE WAIT: Fetching details for '{title[:30]}...'")
            det_resp = requests.get(detail_url, headers=headers)
            if det_resp.status_code == 200:
                det_soup = BeautifulSoup(det_resp.content, 'html.parser')
                
                # Find Link with 'Bill Text' or 'Text of the Bill'
                # Often it's a file attachment
                
                pdf_link = None
                
                # Strategy 1: Look for specific text
                target_texts = ['Bill Text', 'Text of the Bill', 'As Introduced', 'As Passed']
                for t in target_texts:
                    pdf_link = det_soup.find('a', string=re.compile(t, re.IGNORECASE))
                    if pdf_link: break
                
                # Strategy 2: Look for any PDF link in a "downloads" section
                if not pdf_link:
                    # Generic search for pdfs
                    all_links = det_soup.find_all('a', href=True)
                    for a in all_links:
                        if a['href'].lower().endswith('.pdf') and 'bill' in a.get_text().lower():
                            pdf_link = a
                            break

                if pdf_link:
                    pdf_url = pdf_link['href']
                    if not pdf_url.startswith('http'):
                        pdf_url = BASE_URL + pdf_url
                    
                    # Download
                    clean_name = sanitize_filename(title) + ".pdf"
                    save_path = os.path.join(DATASET_DIR, clean_name)
                    
                    with requests.get(pdf_url, stream=True) as r:
                         r.raise_for_status()
                         with open(save_path, 'wb') as f:
                             for chunk in r.iter_content(chunk_size=8192):
                                 f.write(chunk)
                    
                    pdf_filename = clean_name
                    print(f"      ✅ Downloaded: {clean_name}")
                else:
                    print("      ⚠️ No PDF found.")
            
        except Exception as e:
            print(f"      ❌ Error fetching detail: {e}")

        # Add to list
        bill_entry = {
            "Bill_id": f"Bill_{sanitize_filename(title)[:50]}", # Create a slug ID
            "Title": title,
            "Date Introduced": date_intro,
            "Category": category,
            "Status": status,
            "Summary": f"Official bill regarding {title}.",
            "file_path": pdf_filename
        }
        bills_data.append(bill_entry)
        count += 1

    # Save to CSV
    if bills_data:
        df = pd.DataFrame(bills_data)
        df.to_csv(METADATA_FILE, index=False)
        print(f"\n🎉 Successfully saved {len(bills_data)} bills to {METADATA_FILE}")
    else:
        print("\n⚠️ No bills found or parsed.")

def run():
    fetch_bills()

if __name__ == "__main__":
    run()
