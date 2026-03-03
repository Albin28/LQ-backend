@echo off
echo ==================================================
echo      LEGISQ BULK UPLOAD UTILITY
echo ==================================================
echo.
echo This script will DELETE all existing Bills and MPs
echo from the database and upload fresh data from the
echo Excel files in the 'static/dataset' folder.
echo.
echo Make sure your Excel files ('bills.xlsx' and 'mps.xlsx')
echo are up-to-date and correctly formatted before proceeding.
echo.

:choice
set /P c=Are you sure you want to continue? [Y/N]: 
if /I "%c%" EQU "Y" goto :proceed
if /I "%c%" EQU "N" goto :cancel
goto :choice

:proceed
echo.
echo Starting the bulk upload process...
echo Activating virtual environment and running script...
echo.

REM --- Get the directory of the batch file ---
set SCRIPT_DIR=%~dp0

REM --- Activate virtual environment and run the Python script ---
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
python "%SCRIPT_DIR%bulk_upload.py"

echo.
echo Deactivating virtual environment.
call "%SCRIPT_DIR%venv\Scripts\deactivate.bat"

echo.
echo ==================================================
echo      PROCESS COMPLETE
echo ==================================================
pause
exit

:cancel
echo.
echo Operation cancelled by user.
pause
exit
