"""
Example usage of YouTube Data API endpoints.

This file demonstrates how to use the YouTube Data API endpoints
to retrieve video statistics, channel information, and more.
"""

import requests
import json
from typing import List, Dict

# Configuration
BASE_URL = "http://localhost:8000"


def print_response(title: str, data: Dict) -> None:
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2))


def example_1_get_video_stats():
    """Example 1: Get video statistics."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Get Video Statistics")
    print("="*60)
    
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    
    url = f"{BASE_URL}/api/v1/youtube/video/statistics/{video_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nVideo: {data['title']}")
        print(f"Channel: {data['channel_title']}")
        print(f"Duration: {data['duration_formatted']}")
        print(f"Views: {data['view_count']:,}")
        print(f"Likes: {data['like_count']:,}")
        print(f"Comments: {data['comment_count']:,}")
        print(f"Uploaded: {data['upload_date']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_2_get_channel_stats():
    """Example 2: Get channel statistics."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Get Channel Statistics")
    print("="*60)
    
    channel_id = "UC4JX40jDee_NI8pTrqCdO1A"  # Rick Astley
    
    url = f"{BASE_URL}/api/v1/youtube/channel/statistics/{channel_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nChannel: {data['title']}")
        print(f"Subscribers: {data['subscriber_count']:,}")
        print(f"Total Videos: {data['video_count']}")
        print(f"Total Views: {data['total_views']:,}")
        print(f"Country: {data['country']}")
        print(f"Created: {data['created_at']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_3_get_comments():
    """Example 3: Get video comments."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Get Video Comments")
    print("="*60)
    
    video_id = "dQw4w9WgXcQ"
    max_results = 10
    
    url = f"{BASE_URL}/api/v1/youtube/video/comments/{video_id}"
    params = {
        "max_results": max_results,
        "order": "relevance"
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTop {len(data['comments'])} comments:")
        
        for i, comment in enumerate(data['comments'][:5], 1):
            print(f"\n{i}. {comment['author']}")
            print(f"   Text: {comment['text'][:80]}...")
            print(f"   Likes: {comment['likes']:,} | Replies: {comment['reply_count']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_4_search_videos():
    """Example 4: Search for videos."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Search Videos")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/youtube/search"
    params = {
        "query": "machine learning tutorial",
        "max_results": 5,
        "order": "date",
        "region_code": "US"
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nSearch results for '{params['query']}':")
        
        for i, video in enumerate(data['videos'], 1):
            print(f"\n{i}. {video['title']}")
            print(f"   Channel: {video['channel_title']}")
            print(f"   Published: {video['published_at']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_5_trending_videos():
    """Example 5: Get trending videos."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Trending Videos")
    print("="*60)
    
    regions = ["US", "GB", "IN"]
    
    for region in regions:
        url = f"{BASE_URL}/api/v1/youtube/trending"
        params = {
            "region_code": region,
            "max_results": 3
        }
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nTrending in {region}:")
            
            for i, video in enumerate(data['videos'], 1):
                print(f"  {i}. {video['title']}")
                print(f"     Views: {video['view_count']:,}")
        else:
            print(f"Error for {region}: {response.status_code}")


def example_6_related_videos():
    """Example 6: Get related videos."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Related Videos")
    print("="*60)
    
    video_id = "dQw4w9WgXcQ"
    
    url = f"{BASE_URL}/api/v1/youtube/related/{video_id}"
    params = {"max_results": 5}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nVideos related to '{video_id}':")
        
        for i, video in enumerate(data['videos'], 1):
            print(f"\n{i}. {video['title']}")
            print(f"   Channel: {video['channel_title']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_7_get_categories():
    """Example 7: Get video categories."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Video Categories")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/youtube/categories"
    params = {"region_code": "US"}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nAvailable categories ({len(data['categories'])} total):")
        
        for category in data['categories'][:10]:
            print(f"  - {category['title']} (ID: {category['id']})")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_8_combined_analysis():
    """Example 8: Combined analysis (get stats and search related)."""
    print("\n" + "="*60)
    print("EXAMPLE 8: Combined Analysis")
    print("="*60)
    
    video_id = "dQw4w9WgXcQ"
    
    # Get video statistics
    print(f"\nAnalyzing video: {video_id}")
    
    url = f"{BASE_URL}/api/v1/youtube/video/statistics/{video_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"\nStatistics:")
        print(f"  Title: {stats['title']}")
        print(f"  Channel: {stats['channel_title']}")
        print(f"  Views: {stats['view_count']:,}")
        print(f"  Duration: {stats['duration_formatted']}")
        
        # Calculate engagement rate
        engagement_rate = (stats['like_count'] / stats['view_count'] * 100) if stats['view_count'] > 0 else 0
        print(f"  Engagement Rate: {engagement_rate:.2f}%")
        
        # Get related videos
        url = f"{BASE_URL}/api/v1/youtube/related/{video_id}"
        params = {"max_results": 5}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            related = response.json()
            print(f"\nRelated Videos ({len(related['videos'])} found):")
            
            for i, video in enumerate(related['videos'], 1):
                print(f"  {i}. {video['title']}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("YouTube Data API - Example Usage")
    print("="*60)
    print("\nMake sure the FastAPI server is running:")
    print("  python main.py")
    print("\nOr in production:")
    print("  uvicorn main:app --host 0.0.0.0 --port 8000")
    
    examples = [
        ("Video Statistics", example_1_get_video_stats),
        ("Channel Statistics", example_2_get_channel_stats),
        ("Video Comments", example_3_get_comments),
        ("Search Videos", example_4_search_videos),
        ("Trending Videos", example_5_trending_videos),
        ("Related Videos", example_6_related_videos),
        ("Video Categories", example_7_get_categories),
        ("Combined Analysis", example_8_combined_analysis),
    ]
    
    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning all examples...\n")
    
    for name, func in examples:
        try:
            func()
        except requests.exceptions.ConnectionError:
            print(f"\nError: Could not connect to server at {BASE_URL}")
            print("Make sure the FastAPI server is running!")
            return
        except Exception as e:
            print(f"\nError in {name}: {str(e)}")
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
