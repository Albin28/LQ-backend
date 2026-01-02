import os
import pandas as pd

# 1. SETUP PATHS
dataset_folder = "static/dataset"
excel_file = "static/dataset/bills_metadata.xlsx"

print("\n🔍 --- DIAGNOSTIC START ---")

# 2. CHECK FOLDER
if not os.path.exists(dataset_folder):
    print(f"❌ CRITICAL: Folder '{dataset_folder}' NOT FOUND.")
    exit()

files = os.listdir(dataset_folder)
pdf_files = [f for f in files if f.lower().endswith('.pdf')]
print(f"📂 Found {len(pdf_files)} PDFs in folder.")
print(f"👀 First 3 files on disk: {pdf_files[:3]}")

# 3. CHECK EXCEL
if not os.path.exists(excel_file):
    print(f"❌ CRITICAL: Excel file '{excel_file}' NOT FOUND.")
    # Try alternate location just in case
    excel_file = "bills_metadata.xlsx" 
    if os.path.exists(excel_file):
        print(f"✅ Found Excel at root: {excel_file}")
    else:
        exit()

df = pd.read_excel(excel_file).fillna("")
print(f"📊 Found {len(df)} rows in Excel.")

# 4. THE MATCH TEST (The Moment of Truth)
print("\n--- COMPARING FIRST 3 ROWS ---")

for index, row in df.head(3).iterrows():
    # Get Raw ID
    raw_id = str(row.get('Bill ID', 'MISSING_COLUMN'))
    
    # Construct expected filename
    expected_name = f"{raw_id}.pdf"
    
    print(f"\nRow {index + 1}:")
    print(f"   🔹 Excel ID:      '{raw_id}'")  # Quotes show hidden spaces!
    print(f"   🔹 Looking for:   '{expected_name}'")
    
    # Check if it exists exactly
    if expected_name in files:
        print("   ✅ EXACT MATCH FOUND.")
    else:
        print("   ❌ NO EXACT MATCH.")
        # Check case-insensitive
        lower_match = [f for f in files if f.lower() == expected_name.lower()]
        if lower_match:
            print(f"   ⚠️  Found Case-Insensitive Match: '{lower_match[0]}'")
        else:
            print("   💀 File truly not found.")

print("\n-----------------------------")