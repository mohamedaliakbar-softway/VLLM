"""Social platform publisher stubs.

This service abstracts multi-platform video posting. In production,
replace stub methods with real API integrations and OAuth token management.
"""
from __future__ import annotations

import os
import time
import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from config import settings
from pathlib import Path
import requests
from database import SessionLocal
from models import AccountToken

logger = logging.getLogger(__name__)

# For YouTube upload
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logger.warning("YouTube API libraries not available. YouTube publishing will be disabled.")

# For Twitter/X upload
try:
    import tweepy
    from tweepy import OAuthHandler, API
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    logger.warning("Tweepy not available. Twitter/X publishing will be disabled.")


@dataclass
class PublishResult:
    success: bool
    external_post_id: Optional[str] = None
    external_url: Optional[str] = None
    error: Optional[str] = None


class SocialPublisher:
    """Facade for publishing to various platforms.

    Replace stub methods with real API calls. Keep signatures stable.
    """

    def __init__(self):
        pass

    def publish(self, platform: str, file_path: str, text: str, metadata: Optional[Dict] = None) -> PublishResult:
        platform = (platform or "").lower()
        if not os.path.exists(file_path):
            return PublishResult(False, error=f"File not found: {file_path}")

        try:
            if platform in ("linkedin", "li"):
                return self._publish_linkedin(file_path, text, metadata or {})
            if platform in ("instagram", "ig"):
                return self._publish_instagram(file_path, text, metadata or {})
            if platform in ("x", "twitter", "tw"):
                return self._publish_x(file_path, text, metadata or {})
            if platform in ("youtube", "youtube_shorts", "yt"):
                return self._publish_youtube(file_path, text, metadata or {})
            return PublishResult(False, error=f"Unsupported platform: {platform}")
        except Exception as e:
            logger.exception("Publish error")
            return PublishResult(False, error=str(e))

    # ---- Platform stubs ----------------------------------------------------
    
    def _get_token(self, token_id: Optional[str]) -> Optional[AccountToken]:
        if not token_id:
            return None
        db = SessionLocal()
        try:
            return db.query(AccountToken).filter(AccountToken.id == token_id).first()
        finally:
            db.close()

    def _publish_linkedin(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing LinkedIn token")
        access_token = token.access_token
        actor_urn = token.user_id  # store actor URN here, e.g. urn:li:person:xxx or urn:li:organization:yyy
        if not actor_urn:
            return PublishResult(False, error="Missing LinkedIn actor URN in token.user_id")

        headers_auth = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }

        register_body = {
            "registerUploadRequest": {
                "owner": actor_urn,
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "serviceRelationships": [
                    {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                ]
            }
        }

        r = requests.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers_auth,
            data=json.dumps(register_body),
            timeout=60
        )
        if r.status_code >= 300:
            return PublishResult(False, error=f"LinkedIn registerUpload failed: {r.status_code} {r.text}")
        data = r.json()
        upload_mechanism = data.get("value", {}).get("uploadMechanism", {})
        media = upload_mechanism.get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
        upload_url = media.get("uploadUrl")
        asset_urn = data.get("value", {}).get("asset")
        if not upload_url or not asset_urn:
            return PublishResult(False, error="LinkedIn did not return uploadUrl or asset URN")

        with open(file_path, "rb") as f:
            put_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/octet-stream"
            }
            pr = requests.put(upload_url, headers=put_headers, data=f, timeout=600)
            if pr.status_code >= 300:
                return PublishResult(False, error=f"LinkedIn upload failed: {pr.status_code} {pr.text}")

        ugc_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        ugc_body = {
            "author": actor_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text or ""},
                    "shareMediaCategory": "VIDEO",
                    "media": [
                        {
                            "status": "READY",
                            "description": {"text": metadata.get("title") or ""},
                            "media": asset_urn,
                            "title": {"text": metadata.get("title") or ""}
                        }
                    ]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        ur = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=ugc_headers,
            data=json.dumps(ugc_body),
            timeout=60
        )
        if ur.status_code >= 300:
            return PublishResult(False, error=f"LinkedIn post failed: {ur.status_code} {ur.text}")
        post = ur.json()
        external_id = post.get("id") or asset_urn
        external_url = f"https://www.linkedin.com/feed/update/{external_id}" if external_id else None
        return PublishResult(True, external_post_id=external_id, external_url=external_url)

    def _publish_instagram(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing Instagram token")
        access_token = token.access_token
        ig_user_id = token.user_id  # store IG user id here
        video_url = (metadata or {}).get("video_url")
        if not ig_user_id:
            return PublishResult(False, error="Missing Instagram user id in token.user_id")
        if not video_url:
            return PublishResult(False, error="Instagram requires a public video_url for upload via Graph API")

        params = {
            "access_token": access_token,
            "caption": text or "",
            "media_type": "REELS",
            "video_url": video_url,
            "thumb_offset": 0,
            "share_to_feed": "true",
            "is_reels": "true"
        }
        cr = requests.post(f"https://graph.facebook.com/v20.0/{ig_user_id}/media", data=params, timeout=120)
        if cr.status_code >= 300:
            return PublishResult(False, error=f"Instagram creation failed: {cr.status_code} {cr.text}")
        creation_id = cr.json().get("id")
        if not creation_id:
            return PublishResult(False, error="Instagram creation id missing")
        pr = requests.post(f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish", data={
            "access_token": access_token,
            "creation_id": creation_id
        }, timeout=120)
        if pr.status_code >= 300:
            return PublishResult(False, error=f"Instagram publish failed: {pr.status_code} {pr.text}")
        published = pr.json()
        external_id = published.get("id") or creation_id
        external_url = None
        return PublishResult(True, external_post_id=external_id, external_url=external_url)

    def _publish_youtube(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        """
        Upload video to YouTube as a Short.
        
        Requires OAuth 2.0 credentials stored in AccountToken.
        The token should contain:
        - access_token: OAuth 2.0 access token
        - refresh_token: OAuth 2.0 refresh token
        - user_id: YouTube channel ID (optional, can be extracted from token)
        """
        if not YOUTUBE_AVAILABLE:
            return PublishResult(False, error="YouTube API libraries not installed. Install google-api-python-client and google-auth-oauthlib")
        
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing YouTube token. Please connect your YouTube account first.")
        
        try:
            # Create credentials from stored token
            creds = Credentials(
                token=token.access_token,
                refresh_token=token.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret,
            )
            
            # Refresh token if expired
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Update stored token
                    token.access_token = creds.token
                    db = SessionLocal()
                    try:
                        db.commit()
                    finally:
                        db.close()
                except Exception as e:
                    logger.error(f"Failed to refresh YouTube token: {e}")
                    return PublishResult(False, error="YouTube token expired. Please reconnect your account.")
            
            # Build YouTube API client
            youtube = build('youtube', 'v3', credentials=creds)
            
            # Get channel ID if not stored
            channel_id = token.user_id
            if not channel_id:
                try:
                    channels_response = youtube.channels().list(
                        part='id',
                        mine=True
                    ).execute()
                    if channels_response.get('items'):
                        channel_id = channels_response['items'][0]['id']
                        token.user_id = channel_id
                        db = SessionLocal()
                        try:
                            db.commit()
                        finally:
                            db.close()
                except Exception as e:
                    logger.warning(f"Could not get channel ID: {e}")
            
            # Prepare video metadata
            title = metadata.get("title") or (text[:100] if text else "YouTube Short")
            description = text or metadata.get("description", "")
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            elif not isinstance(tags, list):
                tags = []
            
            # YouTube Shorts must be <= 60 seconds and vertical (9:16)
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22',  # People & Blogs (common for Shorts)
                },
                'status': {
                    'privacyStatus': metadata.get("privacy", "public"),  # public, unlisted, private
                    'selfDeclaredMadeForKids': False,
                }
            }
            
            # Upload video
            media = MediaFileUpload(
                file_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            insert_request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute upload with progress tracking
            response = None
            error = None
            retry = 0
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if response is not None:
                        if 'id' in response:
                            video_id = response['id']
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            return PublishResult(
                                True,
                                external_post_id=video_id,
                                external_url=video_url
                            )
                        else:
                            error = f"YouTube upload failed: {response}"
                    elif status:
                        logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        error = f"YouTube upload error: {e}"
                        retry += 1
                        if retry < 3:
                            time.sleep(2 ** retry)
                            continue
                    else:
                        error_msg = f"YouTube API error: {e}"
                        if e.resp.status == 401:
                            error_msg = "YouTube authentication failed. Please reconnect your account."
                        elif e.resp.status == 403:
                            error_msg = "YouTube upload forbidden. Check your API quotas and permissions."
                        return PublishResult(False, error=error_msg)
                except Exception as e:
                    return PublishResult(False, error=f"YouTube upload error: {str(e)}")
            
            return PublishResult(False, error=error or "YouTube upload failed")
            
        except Exception as e:
            logger.exception("YouTube publish error")
            return PublishResult(False, error=f"YouTube upload failed: {str(e)}")

    def _publish_x(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        """
        Upload video to Twitter/X.
        
        Requires OAuth 1.0a credentials stored in AccountToken.
        The token should contain:
        - access_token: OAuth 1.0a access token
        - refresh_token: OAuth 1.0a access token secret (stored in refresh_token field)
        - user_id: Twitter user ID (optional)
        """
        if not TWITTER_AVAILABLE:
            return PublishResult(False, error="Tweepy library not installed. Install tweepy>=4.14.0")
        
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing Twitter/X token. Please connect your Twitter account first.")
        
        try:
            # Get API credentials from environment or settings
            api_key = settings.twitter_api_key or os.getenv("TWITTER_API_KEY")
            api_secret = settings.twitter_api_secret or os.getenv("TWITTER_API_SECRET")
            
            if not api_key or not api_secret:
                return PublishResult(False, error="Twitter API key/secret not configured. Set TWITTER_API_KEY and TWITTER_API_SECRET in .env")
            
            # Initialize Tweepy with OAuth 1.0a
            auth = OAuthHandler(api_key, api_secret)
            auth.set_access_token(token.access_token, token.refresh_token or "")
            api = API(auth, wait_on_rate_limit=True)
            
            # Check file size (Twitter has limits: 512MB for video)
            file_size = os.path.getsize(file_path)
            max_size = 512 * 1024 * 1024  # 512MB for video
            
            if file_size > max_size:
                return PublishResult(False, error=f"Video too large: {file_size / (1024*1024):.1f}MB > 512MB")
            
            # Upload video
            # Twitter API v1.1 media upload endpoint
            try:
                media = api.media_upload(
                    file_path,
                    media_category='tweet_video'  # For video tweets
                )
            except Exception as e:
                logger.error(f"Twitter media upload failed: {e}")
                return PublishResult(False, error=f"Twitter media upload failed: {str(e)}")
            
            # Post tweet with video
            # Truncate text to 280 characters (Twitter limit)
            tweet_text = text[:280] if text else ""
            
            try:
                status = api.update_status(
                    status=tweet_text,
                    media_ids=[media.media_id]
                )
                
                tweet_id = status.id_str
                tweet_url = f"https://twitter.com/{status.user.screen_name}/status/{tweet_id}"
                
                return PublishResult(
                    True,
                    external_post_id=tweet_id,
                    external_url=tweet_url
                )
            except tweepy.TweepyException as e:
                logger.error(f"Twitter status update failed: {e}")
                return PublishResult(False, error=f"Twitter post failed: {str(e)}")
            
        except tweepy.TweepyException as e:
            logger.exception("Twitter/X publish error")
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = "Twitter authentication failed. Please reconnect your account."
            elif "403" in error_msg or "Forbidden" in error_msg:
                error_msg = "Twitter post forbidden. Check your account permissions."
            return PublishResult(False, error=f"Twitter/X upload failed: {error_msg}")
        except Exception as e:
            logger.exception("Twitter/X publish error")
            return PublishResult(False, error=f"Twitter/X upload failed: {str(e)}")


def build_post_text(platform: str, base_text: str, hashtags_csv: Optional[str]) -> str:
    """Compose post text respecting light platform nuances."""
    tags = []
    if hashtags_csv:
        try:
            tags = [t.strip() for t in hashtags_csv.split(',') if t.strip()]
        except Exception:
            tags = []
    # Simple concat; can add char limits later
    text = base_text or ""
    if tags:
        text = f"{text}\n\n{' '.join(tags)}"
    return text.strip()
