# 🚀 Setup Instructions - Local Development

## ✅ Requirements Installed Successfully!

All Python dependencies have been installed. Now you need to configure your environment.

---

## 📋 Step 1: Create .env File

You need to create a `.env` file with your API keys:

```bash
# Copy the example file
copy .env.example .env
```

Or manually create `c:\Users\itza2k\vibeathon\VLLM\.env` with:

```env
# REQUIRED: Get your Gemini API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Server Settings (defaults are fine for local testing)
HOST=127.0.0.1
PORT=8000
DEBUG=true

# YouTube Cookie Settings (helps bypass bot detection)
YOUTUBE_USE_BROWSER_COOKIES=true
YOUTUBE_BROWSER=chrome
```

---

## 🔑 Step 2: Get Gemini API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste it in your `.env` file as `GEMINI_API_KEY=your_key_here`

---

## 🎬 Step 3: Run the Application

### Start Backend:
```bash
cd c:\Users\itza2k\vibeathon\VLLM
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Start Frontend (in a new terminal):
```bash
cd c:\Users\itza2k\vibeathon\VLLM\frontend
npm install  # if first time
npm run dev
```

You should see:
```
VITE ready in XXX ms
➜  Local:   http://localhost:5173/
```

---

## 🧪 Step 4: Test the Application

1. **Open browser**: http://localhost:5173
2. **Enter a YouTube URL**: Try a short video (< 5 minutes)
   - Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ
3. **Click "Generate"**
4. **Watch the progress**:
   - Loading animation with strike-through list ✅
   - Percentage updates 0-100% ✅
   - Video preview after completion ✅

---

## 📊 Expected Processing Flow

### Backend Logs:
```
========== STARTING VIDEO PROCESSING ==========
Job ID: xxx-xxx-xxx
YouTube URL: https://youtube.com/watch?v=...
===============================================
[Extract Transcript] Starting...
[Extract Transcript] ✅ Completed successfully in 2.34s
[Gemini AI Analysis] Starting...
[Gemini AI Analysis] ✅ Completed successfully in 3.12s
[Download Video Segments] Starting...
Downloaded segment 1: temp/VIDEO_ID_segment_1.mp4 (5.23 MB)
[Download Video Segments] ✅ Completed successfully in 6.78s
[Create Shorts] Starting...
Face detected: 245x289px at (432, 156)
Enhanced crop position: (312, 89) with golden ratio composition
✅ Crop applied successfully, resized to 1080x1920
[Create Shorts] ✅ Completed successfully in 8.45s
========== VIDEO PROCESSING ENDED ==========
```

### Frontend Progress:
1. ✅ Connecting to YouTube
2. ✅ Extracting video transcript
3. ✅ Analyzing content with AI
4. ✅ Identifying key highlights
5. ✅ Downloading video segments
6. ✅ Applying smart cropping
7. ✅ Generating short clips
8. ✅ Finalizing your videos

**Total Time**: 15-30 seconds

---

## 🐛 Troubleshooting

### Error: "Field required [type=missing]"
**Solution**: Create `.env` file with `GEMINI_API_KEY`

### Error: "YouTube bot detection"
**Solution**: The code automatically uses browser cookies. Make sure Chrome is installed.

### Error: "Face detection not working"
**Solution**: OpenCV should work automatically. If issues persist:
```bash
pip install --upgrade opencv-python
```

### Error: "ModuleNotFoundError"
**Solution**: Reinstall requirements:
```bash
pip install -r requirements.txt
```

### Port Already in Use
**Solution**: Change port in `.env`:
```env
PORT=8001
```

---

## ✅ Verification Checklist

- [ ] `.env` file created with GEMINI_API_KEY
- [ ] Backend starts without errors
- [ ] Frontend loads at http://localhost:5173
- [ ] Can enter YouTube URL
- [ ] Progress animation shows correctly
- [ ] Video processes successfully
- [ ] Can preview generated shorts

---

## 🎯 Quick Start Commands

```bash
# Terminal 1 - Backend
cd c:\Users\itza2k\vibeathon\VLLM
python main.py

# Terminal 2 - Frontend  
cd c:\Users\itza2k\vibeathon\VLLM\frontend
npm run dev

# Open browser
start http://localhost:5173
```

---

## 📝 Next Steps After Setup

1. **Test with a short video** (< 5 min)
2. **Verify smart cropping** works (face detection)
3. **Check dashboard** for generated highlights
4. **Test export/download** functionality
5. **Optional**: Set up YouTube OAuth for publishing

---

## 🎉 You're Ready!

Once you have your `.env` file configured with the Gemini API key, everything should work perfectly!

**Need help?** Check the logs in both terminals for detailed error messages.
