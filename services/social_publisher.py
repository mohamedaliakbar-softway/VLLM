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
            # Add more (youtube_shorts, tiktok) later
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
