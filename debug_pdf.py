import requests
from bs4 import BeautifulSoup
import re

# Use a specific known bill title fragment to find a link
BASE_URL = "https://prsindia.org"
TRACK_URL = "https://prsindia.org/billtrack"

headers = {'User-Agent': 'Mozilla/5.0'}
print(f"Searching on {TRACK_URL}...")
r = requests.get(TRACK_URL, headers=headers)
soup = BeautifulSoup(r.content, 'html.parser')

target_url = None
for a in soup.find_all('a', href=True):
    # exact search for one of the bills we saw in the CSV
    if "Industrial Relations Code" in a.get_text():
        target_url = BASE_URL + a['href'] if a['href'].startswith('/') else a['href']
        print(f"Found Target: {target_url}")
        break

if not target_url:
    print("Could not find specific bill. Dumping all candidate links:")
    for a in soup.find_all('a', href=True):
        if '/billtrack/' in a['href'] and 'bill' in a.get_text().lower():
             print(f"  Candidate: {a['href']} - {a.get_text()[:30]}")
    exit()

print(f"\nAnalyzing Bill Page: {target_url}")
r2 = requests.get(target_url, headers=headers)
soup2 = BeautifulSoup(r2.content, 'html.parser')

# Dump all links
print("\n--- LINKS ON PAGE ---")
for a in soup2.find_all('a', href=True):
    href = a['href']
    text = a.get_text(strip=True)
    if 'pdf' in href.lower() or 'text' in text.lower():
        print(f"LINK: {href} | TEXT: {text}")

# Look for specific divs
print("\n--- CONTENT DIVS ---")
# PRS often puts content in 'field-name-body' or similar
for div in soup2.find_all('div', class_=re.compile(r'field|content|download')):
    if 'pdf' in div.get_text().lower():
        print(f"DIV ({div.get('class')}): {div.get_text()[:200]}...")
