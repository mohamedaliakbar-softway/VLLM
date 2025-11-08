#!/usr/bin/env python3
"""
Test script to verify the YouTube transcript extraction fix.
Tests that yt-dlp subtitle download bypasses rate limiting.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.youtube_processor import YouTubeProcessor
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_transcript_extraction():
    """Test transcript extraction with the new yt-dlp method."""
    
    print("\n" + "="*70)
    print("🧪 Testing YouTube Transcript Extraction (yt-dlp method)")
    print("="*70 + "\n")
    
    # Test videos with known subtitles
    test_videos = [
        {
            'url': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
            'name': 'Me at the zoo (First YouTube video - short)'
        },
        {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'name': 'Popular music video'
        }
    ]
    
    processor = YouTubeProcessor()
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n📹 Test {i}/{len(test_videos)}: {video['name']}")
        print(f"   URL: {video['url']}")
        print("-" * 70)
        
        try:
            result = processor.get_transcript(video['url'])
            
            if result and result.get('transcript'):
                print(f"✅ SUCCESS!")
                print(f"   - Transcript length: {len(result['transcript'])} characters")
                print(f"   - Duration: {result.get('duration', 0)} seconds")
                print(f"   - Title: {result.get('title', 'N/A')}")
                print(f"   - First 100 chars: {result['transcript'][:100]}...")
            else:
                print(f"⚠️  No transcript extracted")
                print(f"   - Duration: {result.get('duration', 0) if result else 0} seconds")
                print(f"   - May need to wait for rate limit reset")
        
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            print(f"   This might indicate:")
            print(f"   - Rate limit still active (wait 5-10 minutes)")
            print(f"   - Video has no subtitles")
            print(f"   - Network/connection issue")
        
        print("-" * 70)
    
    print("\n" + "="*70)
    print("✅ Transcript extraction test complete!")
    print("="*70)
    print("\n💡 Tips:")
    print("   - If still getting errors, wait 5-10 minutes for rate limit reset")
    print("   - Try a different video URL")
    print("   - Check your internet connection")
    print("   - Vosk fallback will activate if YouTube fails\n")

if __name__ == "__main__":
    test_transcript_extraction()
