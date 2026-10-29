"""
whatsapp_business_plugin.py — WhatsApp Business Cloud API & Messaging Gateway.

Capabilities:
  1. WhatsApp Cloud API: Send template messages, alerts, and customer notifications.
  2. Broadcast Messenger: Dispatches messages across customer contacts.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")


class WhatsAppBusinessPlugin:
    """Manages automated WhatsApp messaging."""

    def send_whatsapp_text(self, recipient_phone: str, text: str, phone_id: str = WHATSAPP_PHONE_ID, token: str = WHATSAPP_TOKEN) -> dict[str, Any]:
        """Send direct text message via WhatsApp Cloud API."""
        clean_number = recipient_phone.replace("+", "").replace(" ", "").replace("-", "")
        if not (phone_id and token):
            return {
                "success": False,
                "reason": "WhatsApp Cloud API credentials not configured (WHATSAPP_PHONE_ID / WHATSAPP_TOKEN).",
                "preview": {"recipient": clean_number, "text": text},
            }

        url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "text",
            "text": {"body": text},
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {token}")

            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "message_id": res.get("messages", [{}])[0].get("id"), "recipient": clean_number}
        except Exception as exc:
            logger.error("WhatsApp Cloud send error: %s", exc)
            return {"success": False, "error": str(exc)}
