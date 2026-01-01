@echo off
:: --- STEP 1: FORCE NAVIGATION TO PROJECT FOLDER ---
:: This ensures the script works even if clicked from Desktop
E:
cd "E:\legisq"

echo ==================================================
echo      LEGISQ "ONE-CLICK" SYSTEM
echo ==================================================
echo.

:: --- STEP 2: ACTIVATE VIRTUAL ENVIRONMENT ---
:: Checks if the venv exists and turns it on
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found. Trying global python...
)

:: --- STEP 3: UPDATE DATABASE (TEXT) ---
echo.
echo [1/3] Updating Firebase Database...
python universal_upload.py

:: --- STEP 4: UPDATE WEBSITE (PDFs) ---
echo.
echo [2/3] Sending PDFs to Cloud (Render)...
git add .
git commit -m "Auto-update via Desktop Shortcut"
git push origin main

echo.
echo ==================================================
echo      SUCCESS! 
echo      1. Text Data is LIVE (Instant).
echo      2. PDF Files will be live in ~2 minutes.
echo ==================================================
echo.
pause