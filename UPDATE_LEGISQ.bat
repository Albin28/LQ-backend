@echo off
cd /d "%~dp0"

echo ==========================================
echo    LEGISQ AUTOMATED UPDATE SYSTEM
echo ==========================================

:: Activate Virtual Environment
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo ⚠️ Venv not found, trying system python...
)

:: Run the Python Pipeline
python universal_upload.py

:: Check if python script succeeded (simple check)
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Pipeline execution failed!
    pause
    exit /b %ERRORLEVEL%
)

:: Git Operations
echo.
echo --- GITHUB SYNC ---
git add .
git commit -m "Auto-update Data: %date% %time%"
git push origin main

echo.
echo ✅ ALL DONE!
pause