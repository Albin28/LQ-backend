@echo off
TITLE LegisQ Master Controller
COLOR 0A

:: --- STEP 1: NAVIGATION (Crucial for Shortcut) ---
:: Forces the computer to go to your project folder
E:
cd "E:\legisq"

echo ==================================================
echo      LEGISQ "ONE-CLICK" MASTER SYSTEM
echo ==================================================
echo.

:: --- STEP 2: ACTIVATE VENV (Crucial for Libraries) ---
:: Turns on the environment where 'firebase_admin' is installed
if exist "venv\Scripts\activate.bat" (
    echo [SYSTEM] Activating Virtual Environment...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found. Using global python...
)

:: --- STEP 3: UPDATE DATABASE (Data) ---
echo.
echo [STEP 1/3] Uploading Excel Data to Firebase...
python universal_upload.py
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python Error! Check your Excel files or install libraries.
    pause
    exit /b
)
echo ✅ Database Synced.

:: --- STEP 4: FORCE PDFs (The New Fix) ---
echo.
echo [STEP 2/3] Locking New PDF Files...
git add .
:: The magic command to force-upload ignored PDFs
git add -f static/dataset/*.pdf
echo ✅ PDFs Locked.

:: --- STEP 5: DEPLOY TO RENDER (Website) ---
echo.
echo [STEP 3/3] Pushing to Render Server...
git commit -m "Auto-Update: New Data and Forced PDFs"
git push origin main
IF %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Git Warning (Nothing new to push).
) ELSE (
    echo ✅ Deployment Triggered!
)

echo.
echo ==================================================
echo      SUCCESS! 
echo      1. Data is LIVE on App immediately.
echo      2. PDFs/Website will refresh in ~2-3 mins.
echo ==================================================
echo.
pause