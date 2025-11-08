#!/bin/bash
# Helper script to export YouTube cookies for yt-dlp

echo "============================================================"
echo "YouTube Cookies Export Helper"
echo "============================================================"
echo ""
echo "This script helps you export YouTube cookies to bypass bot detection."
echo ""

# Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null; then
    echo "❌ yt-dlp is not installed. Please install it first:"
    echo "   pip install yt-dlp"
    exit 1
fi

COOKIES_FILE="./cookies.txt"

echo "Method 1: Export from Browser (Recommended)"
echo "-------------------------------------------"
echo ""
echo "Option A: Using Browser Extension (Easiest)"
echo "  1. Install 'Get cookies.txt LOCALLY' extension:"
echo "     Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"
echo "     Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/"
echo ""
echo "  2. Go to YouTube and sign in"
echo "  3. Click the extension icon"
echo "  4. Select 'youtube.com'"
echo "  5. Click 'Export'"
echo "  6. Save as: $COOKIES_FILE"
echo ""

echo "Option B: Using yt-dlp (Automatic)"
echo "-----------------------------------"
echo ""
echo "Attempting to extract cookies from Chrome..."
echo ""

# Try to extract cookies using yt-dlp
if yt-dlp --cookies-from-browser chrome --cookies "$COOKIES_FILE" "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --skip-download 2>&1 | grep -q "ERROR"; then
    echo "⚠️  Automatic cookie extraction failed."
    echo ""
    echo "This might be because:"
    echo "  - Chrome is locked with a password"
    echo "  - Chrome is not installed"
    echo "  - You need to sign in to YouTube in Chrome first"
    echo ""
    echo "Please use Option A (Browser Extension) instead."
    echo ""
else
    if [ -f "$COOKIES_FILE" ]; then
        echo "✅ Cookies exported successfully to: $COOKIES_FILE"
        echo ""
        echo "Add this to your .env file:"
        echo "  YOUTUBE_COOKIES_FILE=$COOKIES_FILE"
        echo "  YOUTUBE_USE_BROWSER_COOKIES=false"
    else
        echo "⚠️  Cookie extraction completed but file not found."
    fi
fi

echo ""
echo "============================================================"
echo "Next Steps"
echo "============================================================"
echo ""
echo "1. Make sure you're signed into YouTube in your browser"
echo "2. Export cookies using one of the methods above"
echo "3. Add to .env:"
echo "   YOUTUBE_COOKIES_FILE=./cookies.txt"
echo "   YOUTUBE_USE_BROWSER_COOKIES=false"
echo ""
echo "4. Restart your application"
echo ""

