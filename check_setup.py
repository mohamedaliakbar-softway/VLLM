"""Setup verification script for Video Shorts Generator."""
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.9+."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'fastapi',
        'uvicorn',
        'google.genai',
        'pydantic',
        'yt_dlp',
        'moviepy',
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'google.genai':
                __import__('google.genai')
            elif package == 'yt_dlp':
                __import__('yt_dlp')
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - not installed")
            missing.append(package)
    
    return len(missing) == 0, missing

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg: {version_line}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ FFmpeg not found")
    print("   Install: brew install ffmpeg (macOS)")
    print("   Install: sudo apt-get install ffmpeg (Linux)")
    print("   Install: Download from https://ffmpeg.org (Windows)")
    return False

def check_env_file():
    """Check if .env file exists and has required keys."""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Create .env file from .env.example")
        print("   Add your GEMINI_API_KEY")
        return False
    
    # Check for required keys
    with open(env_file) as f:
        content = f.read()
        if 'GEMINI_API_KEY' not in content or 'your_gemini_api_key' in content:
            print("⚠️  .env file exists but GEMINI_API_KEY may not be set")
            print("   Make sure GEMINI_API_KEY is set to your actual API key")
            return False
    
    print("✅ .env file configured")
    return True

def check_directories():
    """Check if required directories exist."""
    dirs = ['temp', 'output']
    all_exist = True
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
        else:
            print(f"✅ Directory exists: {dir_name}")
    
    return True

def main():
    """Run all checks."""
    print("=" * 60)
    print("Video Shorts Generator - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", lambda: check_dependencies()[0]),
        ("FFmpeg", check_ffmpeg),
        ("Environment File", check_env_file),
        ("Directories", check_directories),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! You're ready to use the service.")
        print("\nTo start the server:")
        print("   python main.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nTo install dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()

