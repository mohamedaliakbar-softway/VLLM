# YouTube Bot Detection Fix Guide

## Current Status

✅ **Cookies are configured and working** (tested successfully)
✅ **Browser cookie extraction working** (596 cookies extracted from Chrome)
✅ **Enhanced yt-dlp options added** (user agent, headers, player clients)

## If You're Still Getting Bot Detection Errors

### Quick Fix Steps

1. **Test your cookies:**
   ```bash
   python3 test_youtube_cookies.py
   ```

2. **If test fails, export cookies manually:**
   ```bash
   ./export_youtube_cookies.sh
   ```

3. **Update your `.env` file:**
   ```bash
   # Option A: Use cookies file (most reliable)
   YOUTUBE_COOKIES_FILE=./cookies.txt
   YOUTUBE_USE_BROWSER_COOKIES=false
   
   # Option B: Use browser cookies (if Chrome is unlocked)
   YOUTUBE_USE_BROWSER_COOKIES=true
   YOUTUBE_BROWSER=chrome
   ```

4. **Make sure you're signed into YouTube:**
   - Open Chrome
   - Go to youtube.com
   - Sign in with your Google account
   - Keep Chrome open (don't lock it)

5. **Restart your application** after updating `.env`

## What Was Implemented

### Enhanced Cookie Support
- ✅ Automatic browser cookie extraction (Chrome, Firefox, Safari, Edge, Opera, Brave)
- ✅ Manual cookies file support
- ✅ Fallback between browsers
- ✅ Better error messages

### Anti-Bot Detection Features
- ✅ Modern user agent (Chrome 120)
- ✅ Browser-like HTTP headers
- ✅ Multiple player clients (Android + Web)
- ✅ Retry logic for transient errors
- ✅ Proper referer headers

### Configuration Options

Add to `.env`:
```bash
# Browser cookies (default - works if Chrome is unlocked)
YOUTUBE_USE_BROWSER_COOKIES=true
YOUTUBE_BROWSER=chrome

# OR use cookies file (more reliable)
YOUTUBE_COOKIES_FILE=./cookies.txt
YOUTUBE_USE_BROWSER_COOKIES=false
```

## Troubleshooting

### Error: "Sign in to confirm you're not a bot"

**Solution 1: Export Cookies Manually**
1. Install browser extension: "Get cookies.txt LOCALLY"
   - Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
2. Go to YouTube and sign in
3. Click extension → Select youtube.com → Export
4. Save as `cookies.txt` in project root
5. Add to `.env`: `YOUTUBE_COOKIES_FILE=./cookies.txt`

**Solution 2: Unlock Chrome**
- If Chrome is password-protected, browser cookies won't work
- Either unlock Chrome or use cookies file method

**Solution 3: Try Different Browser**
- Change `YOUTUBE_BROWSER=firefox` in `.env`
- Make sure you're signed into YouTube in Firefox

### Error: "Cookies file not found"

- Make sure the path in `.env` is correct
- Use absolute path if relative path doesn't work
- Check file permissions

### Intermittent Errors

Some videos may still trigger bot detection. This is normal. The system will:
- Retry automatically (3 attempts)
- Use fallback player clients
- Log helpful error messages

## Testing

Run the test script to verify cookies are working:
```bash
python3 test_youtube_cookies.py
```

Expected output:
```
✅ SUCCESS: Browser cookies working!
   Video title: [video title]
```

## Additional Notes

- Cookies expire after some time - you may need to re-export them
- Some videos (especially new/private ones) may have stricter bot detection
- The system uses Android player client as primary (more reliable)
- All yt-dlp calls now include cookie support automatically

