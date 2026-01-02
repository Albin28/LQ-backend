@echo off
TITLE LegisQ Debug Mode
COLOR 0A

:: --- STEP 1: NAVIGATION ---
echo [DEBUG] Navigating to Project Folder...
E:
cd "E:\legisq"
echo Current Directory: %CD%
PAUSE

:: --- STEP 2: ACTIVATE VENV ---
echo.
echo [DEBUG] Checking for Virtual Environment...
if exist "venv\Scripts\activate.bat" (
    echo [SYSTEM] Activating venv...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found. Using global python.
)
PAUSE

:: --- STEP 3: INSTALL LIBRARIES (Just in case) ---
echo.
echo [DEBUG] Ensuring Libraries are Installed...
:: We try to install them silently. If they exist, this skips instantly.
pip install firebase-admin pandas openpyxl
PAUSE

:: --- STEP 4: UPDATE DATABASE ---
echo.
echo [STEP 1/3] Uploading Excel Data...
python universal_upload.py
IF %ERRORLEVEL% NEQ 0 (
    COLOR 0C
    echo.
    echo ❌ CRITICAL ERROR: Python script failed!
    echo Read the error message above (Traceback).
    PAUSE
    goto :EOF
)
echo ✅ Database Synced.
PAUSE

:: --- STEP 5: FORCE PDFs ---
echo.
echo [STEP 2/3] Locking PDFs...
git add .
git add -f static/dataset/*.pdf
echo ✅ PDFs Locked.
PAUSE

:: --- STEP 6: DEPLOY ---
echo.
echo [STEP 3/3] Pushing to Render...
git commit -m "Auto-Update via Debug Script"
git push origin main
echo ✅ Done.

echo.
echo ==================================================
echo      SCRIPT FINISHED CORRECTLY
echo ==================================================
PAUSE