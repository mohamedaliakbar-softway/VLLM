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

    def _publish_linkedin(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        # Simulate upload + processing delay
        time.sleep(1.0)
        fake_id = f"li_{int(time.time()*1000)}"
        fake_url = f"https://www.linkedin.com/feed/update/{fake_id}"
        return PublishResult(True, external_post_id=fake_id, external_url=fake_url)

    def _publish_instagram(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        time.sleep(1.0)
        fake_id = f"ig_{int(time.time()*1000)}"
        fake_url = f"https://www.instagram.com/p/{fake_id}/"
        return PublishResult(True, external_post_id=fake_id, external_url=fake_url)

    def _publish_x(self, file_path: str, text: str, metadata: Dict) -> PublishResult:
        time.sleep(1.0)
        fake_id = f"x_{int(time.time()*1000)}"
        fake_url = f"https://x.com/i/web/status/{fake_id}"
        return PublishResult(True, external_post_id=fake_id, external_url=fake_url)


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
