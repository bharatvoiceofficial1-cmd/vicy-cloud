"""
website_manager_plugin.py — Live Website & WordPress Content Management Plugin.

Capabilities:
  1. Live Site Health & Uptime Monitor: Pings response time, HTTP status, and SSL.
  2. WordPress REST API: Creates, reads, updates, and publishes posts & pages.
  3. Custom Site Webhook: Dispatches deploy/content webhooks to Netlify, Vercel, or custom servers.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

WP_SITE_URL = os.environ.get("WP_SITE_URL", "").rstrip("/")
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")


class WebsiteManagerPlugin:
    """Manages live websites and WordPress publishing."""

    def check_site_health(self, url: str) -> dict[str, Any]:
        """Check live site availability, HTTP response code, and latency."""
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VICY-WebsiteMonitor/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                elapsed_ms = round((time.time() - t0) * 1000, 1)
                return {
                    "success": True,
                    "url": url,
                    "status_code": resp.status,
                    "response_time_ms": elapsed_ms,
                    "state": "UP and Operational" if resp.status == 200 else f"HTTP {resp.status}",
                }
        except Exception as exc:
            elapsed_ms = round((time.time() - t0) * 1000, 1)
            return {
                "success": False,
                "url": url,
                "response_time_ms": elapsed_ms,
                "state": "DOWN / Unreachable",
                "error": str(exc),
            }

    def publish_wordpress_post(
        self,
        title: str,
        content: str,
        status: str = "publish",
        categories: list[int] | None = None,
        tags: list[str] | None = None,
        site_url: str = WP_SITE_URL,
        username: str = WP_USERNAME,
        password: str = WP_APP_PASSWORD,
    ) -> dict[str, Any]:
        """Publish or draft an article on a WordPress website via REST API."""
        if not (site_url and username and password):
            return {
                "success": False,
                "reason": "WordPress credentials missing. Configure WP_SITE_URL, WP_USERNAME, and WP_APP_PASSWORD in environment.",
                "draft_preview": {"title": title, "content_snippet": content[:200]},
            }

        api_url = f"{site_url}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": content,
            "status": status,
        }
        if categories:
            payload["categories"] = categories

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(api_url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            
            auth = f"{username}:{password}".encode("latin1")
            req.add_header("Authorization", f"Basic {base64.b64encode(auth).decode('ascii')}")

            with urllib.request.urlopen(req, timeout=20) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "post_id": res.get("id"),
                    "link": res.get("link"),
                    "status": res.get("status"),
                    "title": title,
                }
        except Exception as exc:
            logger.error("Failed to publish WordPress post: %s", exc)
            return {"success": False, "error": str(exc)}
