"""
plugin_manager.py — Unified Social Media & Live Website MCP/Plugin Manager.

Unifies:
  - YouTube (SEO metadata, search, video stats)
  - Meta Social (Instagram posts, Facebook pages)
  - WhatsApp Business (Customer messaging, alerts)
  - LinkedIn (Article & status publishing)
  - Live Website Manager (Uptime monitor, WordPress article publishing)
"""

from __future__ import annotations

import logging
from typing import Any

from .website_manager_plugin import WebsiteManagerPlugin
from .meta_social_plugin import MetaSocialPlugin
from .youtube_plugin import YouTubePlugin
from .whatsapp_business_plugin import WhatsAppBusinessPlugin
from .linkedin_plugin import LinkedInPlugin

logger = logging.getLogger(__name__)


class SocialWebPluginSuite:
    """Master controller for all social media and live website capabilities."""

    def __init__(self) -> None:
        self.website = WebsiteManagerPlugin()
        self.meta = MetaSocialPlugin()
        self.youtube = YouTubePlugin()
        self.whatsapp = WhatsAppBusinessPlugin()
        self.linkedin = LinkedInPlugin()

    def dispatch(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Route tool/MCP action to appropriate plugin."""
        act = action.lower().strip()

        # ── Website Management ───────────────────────────────────────────────
        if act == "check_site_health":
            url = params.get("url", "")
            return self.website.check_site_health(url)

        elif act == "publish_wordpress_post":
            return self.website.publish_wordpress_post(
                title=params.get("title", ""),
                content=params.get("content", ""),
                status=params.get("status", "publish"),
            )

        # ── YouTube ──────────────────────────────────────────────────────────
        elif act in ("search_youtube", "youtube_search"):
            q = params.get("query", "")
            return self.youtube.search_videos(q)

        elif act in ("youtube_seo", "generate_youtube_metadata"):
            topic = params.get("topic", "")
            return self.youtube.generate_seo_metadata(topic)

        # ── Meta (Instagram & Facebook) ──────────────────────────────────────
        elif act in ("post_facebook", "facebook_post"):
            msg = params.get("message", "")
            link = params.get("link", "")
            return self.meta.publish_facebook_post(msg, link)

        elif act in ("post_instagram", "instagram_post"):
            img = params.get("image_url", "")
            cap = params.get("caption", "")
            return self.meta.publish_instagram_photo(img, cap)

        # ── WhatsApp Business ────────────────────────────────────────────────
        elif act in ("send_whatsapp_business", "whatsapp_broadcast"):
            phone = params.get("phone", "")
            text = params.get("text", "")
            return self.whatsapp.send_whatsapp_text(phone, text)

        # ── LinkedIn ─────────────────────────────────────────────────────────
        elif act in ("post_linkedin", "linkedin_share"):
            text = params.get("text", "")
            url = params.get("article_url", "")
            return self.linkedin.share_update(text, url)

        return {"success": False, "error": f"Unknown social/web plugin action: {action}"}
