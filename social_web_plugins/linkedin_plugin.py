"""
linkedin_plugin.py — LinkedIn Post & Article Sharing Automation.

Capabilities:
  1. Share status updates, articles, and announcements to LinkedIn personal profile or company page.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_AUTHOR_URN = os.environ.get("LINKEDIN_AUTHOR_URN", "")  # e.g. "urn:li:person:XXXX" or "urn:li:organization:XXXX"


class LinkedInPlugin:
    """Manages LinkedIn publishing."""

    def share_update(self, text: str, article_url: str = "", author_urn: str = LINKEDIN_AUTHOR_URN, token: str = LINKEDIN_ACCESS_TOKEN) -> dict[str, Any]:
        """Publish a professional text or link post to LinkedIn."""
        if not (author_urn and token):
            return {
                "success": False,
                "reason": "LinkedIn credentials not configured (LINKEDIN_AUTHOR_URN / LINKEDIN_ACCESS_TOKEN).",
                "preview": {"text": text, "article_url": article_url},
            }

        url = "https://api.linkedin.com/v2/ugcPosts"
        share_content: dict[str, Any] = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE",
        }
        if article_url:
            share_content["shareMediaCategory"] = "ARTICLE"
            share_content["media"] = [{"status": "READY", "originalUrl": article_url}]

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("X-Restli-Protocol-Version", "2.0.0")

            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "post_urn": res.get("id")}
        except Exception as exc:
            logger.error("LinkedIn publish error: %s", exc)
            return {"success": False, "error": str(exc)}
