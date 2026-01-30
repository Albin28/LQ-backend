# 📋 Data Entry & File Naming Config

To prevent "Not Found" errors and duplication issues in the future, follow these strict rules.

## 1. PDF Naming Rules (CRITICAL)
Web servers (Linux) are strict. Windows is lazy.
Always format your PDF filenames like this:

*   ✅ **DO:** `bill_101.pdf` (All lowercase, Underscores for spaces)
*   ✅ **DO:** `finance_bill_2024.pdf`
*   ❌ **DON'T:** `Bill 101.pdf` (No spaces!)
*   ❌ **DON'T:** `Bill_101.PDF` (No uppercase extensions!)
*   ❌ **DON'T:** `Bill/101.pdf` (No slashes!)

**Rule of Thumb:** **"Lowersnake Case"** -> `all_lowercase_with_underscores.pdf`

## 2. Excel Sheet Rules
Your `bills_metadata.xlsx` should match your filenames.

*   **Column:** `Bill ID` (or `Bill_id`)
*   **Value:** Should match the filename (without `.pdf`).

**Example:**
| Bill ID | Date | Title | Actual File Required |
| :--- | :--- | :--- | :--- |
| `bill_101` | 2024-01-01 | My Bill | `bill_101.pdf` |
| `finance_23` | 2024-02-01 | Finance | `finance_23.pdf` |

## 3. Deployment Checklist
When you add new files:
1.  Paste the PDF into `static/dataset/`.
2.  Update the Excel row.
3.  **Run the update script** (or `reset_db.py` if replacing old data).
4.  **GIT PUSH:**
    *   `git add .`
    *   `git commit -m "added new bills"`
    *   `git push`

If you don't `git push`, the PDFs effectively "don't exist" on the live website.
