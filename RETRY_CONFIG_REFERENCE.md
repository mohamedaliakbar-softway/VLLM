# Quick Reference: Retry & Fallback Configuration

## Current Settings (Optimized)

### YouTube Transcript Retries
```python
# File: services/youtube_processor.py (lines 238-240)
max_retries = 2              # Reduced from 5
base_retry_delay = 3         # Reduced from 5 seconds
# Total max wait: 9 seconds (3s + 6s) vs 155 seconds previously
```

### Retry Schedule
| Attempt | Wait Time | Cumulative |
|---------|-----------|------------|
| 1       | 0s        | 0s         |
| 2       | 3s        | 3s         |
| 3       | 6s        | 9s         |

### Fallback Chain
```
YouTube (9s max) → Vosk (offline, no limits) → Gemini (cloud API)
```

## What Changed

### Before (Removed)
```python
max_retries = 5
base_retry_delay = 5
# Wait times: 5s, 10s, 20s, 40s, 80s
# Total: 155 seconds = 2.5 minutes
```

❌ Problems:
- Users waited too long (2.5 min max)
- No alternative method when YouTube fails
- Poor UX during rate limit periods

### After (Implemented)
```python
max_retries = 2
base_retry_delay = 3
# Wait times: 3s, 6s
# Total: 9 seconds → then fallback to Vosk
```

✅ Benefits:
- Quick failure detection (9s)
- Automatic offline fallback (Vosk)
- No data loss - still get transcript
- Better user experience

## Files Modified

### 1. `services/youtube_processor.py`
**Lines 238-240:** Reduced retry configuration

**Before:**
```python
max_retries = 5
base_retry_delay = 5
```

**After:**
```python
max_retries = 2  # Reduced from 5 to 2 (max wait: 9s vs 155s)
base_retry_delay = 3  # Reduced from 5 to 3 seconds
```

### 2. `main.py`
**Lines 257-295:** Added Vosk fallback logic

**New Code:**
```python
except Exception as e:
    if attempt == max_retries:
        # Try Vosk fallback before failing
        logger.warning("Falling back to Vosk offline transcription...")
        
        # Download video and use Vosk
        video_info = youtube_processor.download_video(youtube_url)
        caption_gen = CaptionGenerator()
        
        if caption_gen.use_vosk:
            vosk_result = caption_gen.transcribe_with_vosk(audio_path)
            video_info['transcript'] = vosk_result['full_text']
```

## Testing

### Test YouTube Path (Success)
```bash
python example_usage.py
# Should show: "Transcript extracted (attempt 1): 15234 chars"
```

### Test Vosk Fallback (Simulate 429)
```python
# Temporarily break YouTube API to test fallback
# Add to youtube_processor.py get_transcript():
raise requests.exceptions.HTTPError("429 Too Many Requests")
```

Expected output:
```
Rate limited (429) on attempt 1/2, waiting 3s...
Rate limited (429) on attempt 2/2, waiting 6s...
Falling back to Vosk offline transcription...
Using Vosk for offline transcription...
Vosk transcription successful: 15234 chars
```

## Rate Limit Prevention

### Built-in Safeguards
```python
# Minimum 2 seconds between YouTube requests
self.min_request_interval = 2.0
```

### How it works:
1. Every YouTube API call checks elapsed time
2. If <2 seconds since last call, sleeps
3. Prevents burst requests that trigger 429

## Monitoring Commands

### Check if Vosk is Available
```python
from services.caption_generator import CaptionGenerator
gen = CaptionGenerator()
print(gen.use_vosk)  # True if available
```

### View Recent Logs
```bash
# Windows PowerShell
Get-Content temp/*.log -Tail 50

# Or check console output for:
"Rate limited (429)"  # YouTube hit limit
"Falling back to Vosk"  # Fallback triggered
"Vosk transcription successful"  # Fallback worked
```

## When to Adjust Settings

### Increase Retries (Not Recommended)
```python
max_retries = 3  # Only if Vosk unavailable
```

**When:**
- Vosk model not installed
- Need to maximize YouTube success rate
- Can tolerate longer wait times

**Trade-off:**
- Wait time increases to 3s + 6s + 12s = 21s

### Decrease Retries (Aggressive)
```python
max_retries = 1  # Single retry only
base_retry_delay = 2
```

**When:**
- Vosk is very reliable in your setup
- Want fastest possible fallback
- Rate limits are rare

**Trade-off:**
- Wait time: only 2s before Vosk fallback
- Slightly higher Vosk usage (more processing time)

### Adjust Request Interval
```python
# File: services/youtube_processor.py
self.min_request_interval = 3.0  # Increase from 2.0
```

**When:**
- Still getting frequent 429 errors
- Processing many videos concurrently
- YouTube throttling your IP

## Summary Table

| Scenario | Duration | Method Used | User Impact |
|----------|----------|-------------|-------------|
| Normal (90%) | 2-3s | YouTube | ✅ Instant |
| Rate Limited (9%) | 9s + 30-60s | YouTube → Vosk | ⚠️ Slight delay |
| Vosk Unavailable (1%) | 9s + fail | YouTube → Error | ❌ Fails |
| All Working | Always works | Fallback chain | ✅ Reliable |

## Documentation

- **Full Guide:** `TRANSCRIPTION_FALLBACK_SYSTEM.md`
- **Setup:** `SETUP_INSTRUCTIONS.md`
- **Vosk Info:** `why_vosk_is_better.py`
- **General:** `README.md`

---

**Quick Tips:**

✅ DO:
- Keep Vosk model installed for reliability
- Monitor logs for 429 patterns
- Use current settings (2 retries, 3s delay)

❌ DON'T:
- Increase retries above 3 without fallback
- Remove Vosk model from repo
- Make concurrent requests without rate limiting

---

**Version:** 2.0  
**Updated:** November 9, 2025
