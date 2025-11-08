#!/usr/bin/env python3
"""
Test Vosk offline transcription directly.
This bypasses YouTube entirely and tests the fallback system.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.caption_generator import CaptionGenerator
from services.youtube_processor import YouTubeProcessor
import logging
import tempfile

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_vosk_with_youtube_video():
    """Download a video and transcribe with Vosk."""
    
    print("\n" + "="*70)
    print("🎤 Testing Vosk Offline Transcription")
    print("="*70 + "\n")
    
    # Use a short video for quick testing
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    print(f"📹 Test video: {test_url}")
    print(f"   (Me at the zoo - First YouTube video, 19 seconds)")
    print("-" * 70)
    
    try:
        # Step 1: Download video
        print("\n📥 Step 1: Downloading video...")
        processor = YouTubeProcessor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "test_video.mp4")
            
            # Download just the video (no transcript needed)
            print("   Downloading with yt-dlp...")
            import yt_dlp
            
            ydl_opts = {
                'format': 'worst[ext=mp4]',  # Use worst quality for speed
                'outtmpl': video_path,
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([test_url])
            
            if not os.path.exists(video_path):
                print("❌ Video download failed")
                return False
            
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
            print(f"✅ Video downloaded: {file_size:.2f} MB")
            
            # Step 2: Transcribe with Vosk
            print("\n🎤 Step 2: Transcribing with Vosk...")
            print("   (This may take 20-30 seconds for a 19-second video)")
            
            caption_gen = CaptionGenerator()
            transcript = caption_gen.transcribe_with_vosk(video_path)
            
            if transcript:
                print(f"\n✅ SUCCESS! Vosk transcription completed")
                print(f"   - Transcript length: {len(transcript)} characters")
                print(f"   - Word count: {len(transcript.split())} words")
                print(f"\n📝 Transcript preview:")
                print(f"   \"{transcript[:200]}...\"")
                
                # Verify it's not empty
                if len(transcript) > 10:
                    print(f"\n🎉 Vosk is working perfectly!")
                    print(f"   ✅ Can transcribe audio offline")
                    print(f"   ✅ No YouTube API needed")
                    print(f"   ✅ No rate limits")
                    return True
                else:
                    print(f"\n⚠️  Transcript too short, may indicate an issue")
                    return False
            else:
                print(f"❌ Vosk transcription returned empty")
                return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def test_vosk_availability():
    """Quick test to check if Vosk is available."""
    print("\n" + "="*70)
    print("🔍 Checking Vosk Installation")
    print("="*70 + "\n")
    
    try:
        from vosk import Model, KaldiRecognizer
        print("✅ Vosk library is installed")
        
        # Check if model exists
        model_path = "vosk-model-small-en-us-0.15"
        if os.path.exists(model_path):
            print(f"✅ Vosk model found: {model_path}")
            
            # Try to load model
            try:
                model = Model(model_path)
                print("✅ Vosk model loaded successfully")
                return True
            except Exception as e:
                print(f"⚠️  Model exists but failed to load: {e}")
                return False
        else:
            print(f"❌ Vosk model not found at: {model_path}")
            print(f"\n💡 To download the model:")
            print(f"   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
            print(f"   unzip vosk-model-small-en-us-0.15.zip")
            return False
    
    except ImportError:
        print("❌ Vosk library not installed")
        print("\n💡 To install Vosk:")
        print("   pip install vosk")
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 VOSK OFFLINE TRANSCRIPTION TEST")
    print("="*70)
    
    # First check if Vosk is available
    if not test_vosk_availability():
        print("\n" + "="*70)
        print("❌ Vosk is not properly set up")
        print("="*70)
        print("\n💡 Setup instructions:")
        print("   1. pip install vosk")
        print("   2. Download model: wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print("   3. unzip vosk-model-small-en-us-0.15.zip")
        print("   4. Run this test again")
        sys.exit(1)
    
    # Now test actual transcription
    print("\n")
    success = test_vosk_with_youtube_video()
    
    print("\n" + "="*70)
    if success:
        print("✅ VOSK TEST PASSED!")
        print("="*70)
        print("\n🎉 Your system can transcribe videos offline!")
        print("   - No YouTube API needed")
        print("   - No rate limits")
        print("   - Works even when YouTube blocks you")
        print("\n💡 This means your video generation will work even with YouTube rate limits!")
    else:
        print("❌ VOSK TEST FAILED")
        print("="*70)
        print("\n⚠️  Check the errors above and ensure:")
        print("   - Vosk is installed: pip install vosk")
        print("   - Model is downloaded and extracted")
        print("   - FFmpeg is installed (for audio extraction)")
    
    print("\n")
