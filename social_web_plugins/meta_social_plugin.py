"""
meta_social_plugin.py — Instagram & Facebook Automation Plugin.

Capabilities:
  1. Instagram Graph API: Post media, publish captions, schedule reels, retrieve insights.
  2. Facebook Page Management: Publish updates, post links, read engagement.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")


class MetaSocialPlugin:
    """Automates Facebook Pages and Instagram Business accounts."""

    def publish_facebook_post(self, message: str, link: str = "", page_id: str = FB_PAGE_ID, token: str = META_ACCESS_TOKEN) -> dict[str, Any]:
        """Publish a status or link to Facebook Page."""
        if not (page_id and token):
            return {
                "success": False,
                "reason": "Facebook credentials not configured (FB_PAGE_ID / META_ACCESS_TOKEN).",
                "preview": {"message": message, "link": link},
            }

        url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        payload: dict[str, Any] = {"message": message, "access_token": token}
        if link:
            payload["link"] = link

        try:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "post_id": res.get("id"), "message": message}
        except Exception as exc:
            logger.error("Facebook post error: %s", exc)
            return {"success": False, "error": str(exc)}

    def publish_instagram_photo(self, image_url: str, caption: str, ig_user_id: str = IG_USER_ID, token: str = META_ACCESS_TOKEN) -> dict[str, Any]:
        """Publish image post with caption to Instagram Business Account."""
        if not (ig_user_id and token):
            return {
                "success": False,
                "reason": "Instagram credentials not configured (IG_USER_ID / META_ACCESS_TOKEN).",
                "preview": {"image_url": image_url, "caption": caption},
            }

        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
        container_data = urllib.parse.urlencode({
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(container_url, data=container_data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                creation_id = res.get("id")

            # Step 2: Publish media container
            publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
            pub_data = urllib.parse.urlencode({
                "creation_id": creation_id,
                "access_token": token,
            }).encode("utf-8")

            req2 = urllib.request.Request(publish_url, data=pub_data, method="POST")
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                res2 = json.loads(resp2.read().decode("utf-8"))
                return {"success": True, "instagram_post_id": res2.get("id"), "caption": caption}
        except Exception as exc:
            logger.error("Instagram publish error: %s", exc)
            return {"success": False, "error": str(exc)}
