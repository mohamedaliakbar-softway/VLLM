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
from datetime import datetime

from config import settings
from pathlib import Path
import requests
from database import SessionLocal
from models import AccountToken

# YouTube API imports
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

logger = logging.getLogger(__name__)


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
                return self._publish_youtube_shorts(file_path, text, metadata or {})
            if platform in ("tiktok", "tt"):
                return self._publish_tiktok(file_path, text, metadata or {})
            if platform in ("facebook", "fb"):
                return self._publish_facebook(file_path, text, metadata or {})
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

    def _publish_x(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        return PublishResult(False, error="X/Twitter upload not configured: requires API key/secret and OAuth 1.0a user tokens")

    def _publish_youtube_shorts(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        """Publish video to YouTube Shorts using YouTube Data API v3.
        
        Requires:
        - OAuth 2.0 token with youtube.upload scope
        - Google Cloud project with YouTube Data API v3 enabled
        - Video file must be in supported format (MP4, MOV, etc.)
        
        Implementation steps:
        1. Authenticate with OAuth 2.0 token
        2. Upload video using resumable upload API
        3. Set metadata (title, description, tags, category, privacy)
        4. Return video ID and URL
        """
        if not YOUTUBE_API_AVAILABLE:
            return PublishResult(
                False,
                error="YouTube API client not available. Please install google-api-python-client."
            )
        
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing YouTube OAuth token. Please connect your YouTube account.")
        
        try:
            # Get OAuth client credentials from config (needed for token refresh)
            client_id = settings.youtube_client_id
            client_secret = settings.youtube_client_secret
            
            # Create credentials from stored token
            creds_data = {
                "token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
            }
            
            # Create credentials - will auto-refresh if needed
            credentials = Credentials.from_authorized_user_info(creds_data)
            
            # Check if token is expired and refresh if needed
            if token.expires_at and token.expires_at < datetime.utcnow():
                if not token.refresh_token:
                    return PublishResult(False, error="YouTube token expired and no refresh token available. Please reconnect your account.")
                
                # Attempt to refresh the token
                try:
                    from google.auth.transport.requests import Request as GoogleRequest
                    credentials.refresh(GoogleRequest())
                    
                    # Update token in database
                    db = SessionLocal()
                    try:
                        updated_token = db.query(AccountToken).filter(AccountToken.id == token.id).first()
                        if updated_token:
                            updated_token.access_token = credentials.token
                            if credentials.refresh_token:
                                updated_token.refresh_token = credentials.refresh_token
                            if credentials.expiry:
                                updated_token.expires_at = credentials.expiry
                            db.commit()
                            logger.info(f"YouTube token refreshed successfully for token {token.id}")
                    finally:
                        db.close()
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh YouTube token: {str(refresh_error)}")
                    return PublishResult(False, error=f"YouTube token expired and refresh failed: {str(refresh_error)}. Please reconnect your account.")
            
            # Build YouTube service
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Prepare video metadata
            title = metadata.get("title") or text.split('\n')[0] or "YouTube Short"
            description = text or metadata.get("description") or ""
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # YouTube Shorts must be <= 60 seconds and vertical (9:16)
            body = {
                'snippet': {
                    'title': title[:100],  # YouTube title limit is 100 chars
                    'description': description[:5000],  # YouTube description limit is 5000 chars
                    'tags': tags[:10],  # YouTube allows max 10 tags
                    'categoryId': '22'  # People & Blogs category (can be customized)
                },
                'status': {
                    'privacyStatus': metadata.get("privacy", "public"),  # public, unlisted, private
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Upload video using resumable upload
            media = MediaFileUpload(
                file_path,
                chunksize=-1,  # Use resumable upload
                resumable=True,
                mimetype='video/*'
            )
            
            # Insert video
            insert_request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute upload with resumable support
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")
            
            if 'id' in response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"YouTube Short uploaded successfully: {video_url}")
                return PublishResult(
                    True,
                    external_post_id=video_id,
                    external_url=video_url
                )
            else:
                return PublishResult(False, error="YouTube upload completed but no video ID returned")
                
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            error_message = error_details.get('error', {}).get('message', str(e))
            logger.error(f"YouTube API error: {error_message}")
            return PublishResult(False, error=f"YouTube API error: {error_message}")
        except Exception as e:
            logger.exception("YouTube upload error")
            return PublishResult(False, error=f"YouTube upload failed: {str(e)}")

    def _publish_tiktok(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        """Publish video to TikTok using TikTok API.
        
        Requires:
        - TikTok Business API access
        - OAuth token with video upload permissions
        - Video must meet TikTok requirements (format, duration, etc.)
        """
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing TikTok OAuth token. Please connect your TikTok account.")
        
        # TODO: Implement TikTok upload
        # This requires TikTok Business API integration
        
        return PublishResult(
            False,
            error="TikTok publishing not yet fully implemented. Requires TikTok Business API integration."
        )

    def _publish_facebook(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        """Publish video to Facebook Reels using Facebook Graph API.
        
        Requires:
        - Facebook Page access token
        - Video URL (Facebook requires public URL for upload)
        - Page ID where video will be posted
        """
        token_id = (metadata or {}).get("token_id")
        token = self._get_token(token_id)
        if not token:
            return PublishResult(False, error="Missing Facebook access token. Please connect your Facebook account.")
        
        page_id = token.user_id  # Store Facebook Page ID in token.user_id
        if not page_id:
            return PublishResult(False, error="Missing Facebook Page ID in token.user_id")
        
        video_url = (metadata or {}).get("video_url")
        if not video_url:
            return PublishResult(False, error="Facebook requires a public video_url for upload via Graph API")
        
        # TODO: Implement Facebook Reels upload
        # Similar to Instagram but using Facebook Graph API
        
        return PublishResult(
            False,
            error="Facebook Reels publishing not yet fully implemented. Requires Facebook Graph API integration."
        )


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
