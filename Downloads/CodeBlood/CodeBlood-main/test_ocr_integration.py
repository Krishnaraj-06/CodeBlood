"""
Test script to verify OCR integration is working correctly
"""
import os
from pathlib import Path

def check_requirements():
    """Check if all required files and directories exist"""
    print("🔍 Checking OCR Integration Setup...\n")
    
    checks = []
    
    # Check files
    files_to_check = [
        ('server.py', 'Flask server with OCR routes'),
        ('gemini.py', 'Gemini OCR extraction function'),
        ('templates/ocr_dashboard.html', 'OCR dashboard template'),
        ('templates/base.html', 'Base template'),
        ('.env.example', 'Environment variables example'),
        ('requirements.txt', 'Python dependencies'),
        ('OCR_SETUP.md', 'Setup documentation'),
    ]
    
    for file_path, description in files_to_check:
        exists = Path(file_path).exists()
        status = "✅" if exists else "❌"
        checks.append(exists)
        print(f"{status} {file_path:<35} - {description}")
    
    # Check directories
    print("\n📁 Checking Directories:")
    dirs_to_check = [
        ('uploads', 'Upload directory for files and CSV output'),
        ('templates', 'Flask templates directory'),
        ('static', 'Static files directory'),
    ]
    
    for dir_path, description in dirs_to_check:
        exists = Path(dir_path).exists()
        status = "✅" if exists else "❌"
        checks.append(exists)
        print(f"{status} {dir_path:<35} - {description}")
    
    # Check environment
    print("\n🔑 Checking Environment:")
    env_exists = Path('.env').exists()
    env_status = "✅" if env_exists else "⚠️"
    print(f"{env_status} .env file {'exists' if env_exists else 'NOT FOUND - Copy .env.example to .env'}")
    
    if env_exists:
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            print(f"✅ GEMINI_API_KEY is set ({api_key[:10]}...)")
        else:
            print("⚠️  GEMINI_API_KEY not found in .env")
            checks.append(False)
    else:
        checks.append(False)
    
    # Check imports
    print("\n📦 Checking Python Dependencies:")
    required_packages = [
        'flask',
        'pandas',
        'requests',
        'dotenv',
        'werkzeug',
        'PIL',
    ]
    
    for package in required_packages:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            elif package == 'PIL':
                __import__('PIL')
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Run: pip install -r requirements.txt")
            checks.append(False)
    
    # Summary
    print("\n" + "="*60)
    if all(checks):
        print("✅ All checks passed! OCR integration is ready.")
        print("\n🚀 To start the server:")
        print("   1. Ensure .env has your GEMINI_API_KEY")
        print("   2. Run: python server.py")
        print("   3. Visit: http://localhost:8501/ocr-dashboard")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
    print("="*60)

if __name__ == "__main__":
    check_requirements()
