"""Example usage of the Video Shorts Generator API."""
import requests
import json
import time

# API endpoint
API_BASE_URL = "http://localhost:8000"

def generate_shorts_example(youtube_url: str, max_shorts: int = 3):
    """
    Example: Generate marketing shorts from a YouTube video.
    
    Args:
        youtube_url: YouTube video URL (15-30 minutes)
        max_shorts: Maximum number of shorts to generate (default: 3)
    """
    print(f"🚀 Generating shorts from: {youtube_url}")
    print(f"📊 Requesting up to {max_shorts} highlights...\n")
    
    # Make API request
    response = requests.post(
        f"{API_BASE_URL}/api/v1/generate-shorts",
        json={
            "youtube_url": youtube_url,
            "max_shorts": max_shorts
        },
        timeout=600  # 10 minutes timeout for long videos
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("✅ Success! Generated shorts:\n")
        print(f"📹 Video: {result['video_title']}")
        print(f"⏱️  Duration: {result['video_duration']} seconds")
        print(f"🎬 Generated {len(result['shorts'])} shorts\n")
        print("=" * 60)
        
        for short in result['shorts']:
            print(f"\n🎯 Short #{short['short_id']}")
            print(f"   ⏰ Time: {short['start_time']} - {short['end_time']}")
            print(f"   📏 Duration: {short['duration_seconds']} seconds")
            print(f"   ⭐ Engagement Score: {short['engagement_score']}/10")
            print(f"   💡 Why it works: {short['marketing_effectiveness']}")
            print(f"   📢 Suggested CTA: {short['suggested_cta']}")
            print(f"   📥 Download: {API_BASE_URL}{short['download_url']}")
            print("-" * 60)
        
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
        return None


def download_short_example(filename: str, output_path: str = None):
    """
    Example: Download a generated short.
    
    Args:
        filename: Short video filename
        output_path: Local path to save the file (optional)
    """
    print(f"📥 Downloading: {filename}")
    
    response = requests.get(
        f"{API_BASE_URL}/api/v1/download/{filename}",
        stream=True
    )
    
    if response.status_code == 200:
        if not output_path:
            output_path = filename
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded to: {output_path}")
        return output_path
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
        return None


if __name__ == "__main__":
    # Example usage
    print("=" * 60)
    print("Video Shorts Generator - Example Usage")
    print("=" * 60)
    print()
    
    # Replace with your YouTube URL
    youtube_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
    
    # Check if URL is provided
    if "YOUR_VIDEO_ID" in youtube_url:
        print("⚠️  Please update the youtube_url variable with a real YouTube URL")
        print("   Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print()
        print("   Make sure:")
        print("   - Video is 15-30 minutes long")
        print("   - Video is publicly accessible")
        print("   - API server is running (python main.py)")
        exit(1)
    
    # Generate shorts
    result = generate_shorts_example(youtube_url, max_shorts=3)
    
    if result:
        # Optionally download the first short
        if result['shorts']:
            first_short = result['shorts'][0]
            print(f"\n📥 Downloading first short: {first_short['filename']}")
            download_short_example(
                first_short['filename'],
                f"downloaded_{first_short['filename']}"
            )

