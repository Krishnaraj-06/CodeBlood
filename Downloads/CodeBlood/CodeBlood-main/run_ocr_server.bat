@echo off
echo Starting Attendance Anomaly OCR Server...
echo.

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and add your GEMINI_API_KEY
    echo.
    pause
    exit /b 1
)

REM Create uploads directory if it doesn't exist
if not exist uploads mkdir uploads

REM Run the Flask server
python server.py

pause
