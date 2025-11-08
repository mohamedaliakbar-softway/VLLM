#!/usr/bin/env python3
"""Test YouTube cookie extraction and yt-dlp configuration."""
import sys
import yt_dlp
from pathlib import Path

def test_cookies():
    """Test if cookies are working with yt-dlp."""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Test video
    
    print("Testing YouTube cookie configuration...")
    print("=" * 60)
    print()
    
    # Test 1: Browser cookies (Chrome)
    print("Test 1: Browser cookies (Chrome)")
    print("-" * 60)
    try:
        opts = {
            'quiet': False,
            'cookiesfrombrowser': ('chrome',),
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            print(f"✅ SUCCESS: Browser cookies working!")
            print(f"   Video title: {info.get('title', 'N/A')[:50]}...")
            return True
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        print()
    
    # Test 2: Cookies file
    print()
    print("Test 2: Cookies file")
    print("-" * 60)
    cookies_file = Path("./cookies.txt")
    if cookies_file.exists():
        try:
            opts = {
                'quiet': False,
                'cookiefile': str(cookies_file),
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
                print(f"✅ SUCCESS: Cookies file working!")
                print(f"   Video title: {info.get('title', 'N/A')[:50]}...")
                return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
    else:
        print(f"⚠️  Cookies file not found: {cookies_file}")
        print("   Run: ./export_youtube_cookies.sh to create it")
    
    print()
    print("=" * 60)
    print("RECOMMENDATION:")
    print("=" * 60)
    print()
    print("Browser cookies might not work if:")
    print("  - Chrome is password-protected")
    print("  - You're not signed into YouTube")
    print("  - Browser cookies are encrypted")
    print()
    print("SOLUTION: Export cookies manually")
    print("  1. Install browser extension: Get cookies.txt LOCALLY")
    print("  2. Go to YouTube and sign in")
    print("  3. Export cookies to cookies.txt")
    print("  4. Add to .env: YOUTUBE_COOKIES_FILE=./cookies.txt")
    print("  5. Add to .env: YOUTUBE_USE_BROWSER_COOKIES=false")
    print()
    
    return False

if __name__ == "__main__":
    success = test_cookies()
    sys.exit(0 if success else 1)

