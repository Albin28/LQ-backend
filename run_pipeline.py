import fetch_bills
import fetch_mps
import os
import sys

def main():
    print("🚀 STARTING LEGISQ DATA PIPELINE...")
    print("=========================================")

    # Step 1: Get Bills
    print("\n--- 1. FETCHING BILLS ---")
    try:
        fetch_bills.run()
    except Exception as e:
        print(f"❌ Error in fetch_bills: {e}")

    # Step 2: Get MPs
    print("\n--- 2. FETCHING MP SCORES ---")
    try:
        fetch_mps.run()
    except Exception as e:
        print(f"❌ Error in fetch_mps: {e}")

    # Step 3: Upload to Database
    print("\n--- 3. SYNCING TO FIREBASE ---")
    try:
        # Check if universal_upload exists
        if os.path.exists("universal_upload.py"):
            # Using os.system to run it as a separate process to avoid import conflicts or context issues
            # though importing would also work if written as a module.
            # The prompt suggested os.system/subprocess.
            exit_code = os.system("python universal_upload.py")
            if exit_code != 0:
                print("❌ Upload script failed.")
        else:
             print("❌ universal_upload.py not found!")
    except Exception as e:
        print(f"❌ Error executing upload: {e}")

    print("\n=========================================")
    print("✅ PIPELINE FINISHED! Review output above.")
    print("   If successful, the .bat file will now push to Git.")

if __name__ == "__main__":
    main()
