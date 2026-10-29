"""
notifier.py — Autonomous Multi-Channel Notification Engine for Avi.

Notification Priority:
  1. Desktop Mode (PC is ON): Local Voice TTS + Windows Toast Notification.
  2. Cloud Mode (PC is OFF / Shutdown):
     - Step 1: Voice Phone Call to Avi (+918840795166).
     - Step 2: SMS notification if call not answered or Twilio SMS configured.
     - Step 3: Email notification with full report to bharatvoiceofficial1@gmail.com.
"""

from __future__ import annotations

import logging
import os
import smtplib
import urllib.parse
import urllib.request
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PHONE = os.environ.get("AVI_PHONE", "+918840795166")
DEFAULT_EMAIL = os.environ.get("AVI_EMAIL", "bharatvoiceofficial1@gmail.com")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


class Notifier:
    """Manages phone calls, SMS, email, and desktop alerts."""

    def __init__(
        self,
        phone: str = DEFAULT_PHONE,
        email: str = DEFAULT_EMAIL,
    ) -> None:
        self.phone = phone
        self.email = email

    # ── Voice Phone Call ────────────────────────────────────────────────────────

    def place_voice_call(self, message: str) -> dict[str, Any]:
        """Call Avi's phone via Twilio Voice API with interactive TwiML speech."""
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
            logger.info("Twilio credentials not configured yet. Queuing SMS/Email fallback.")
            return {
                "success": False,
                "reason": "Twilio credentials missing. Configure TWILIO_ACCOUNT_SID & TWILIO_AUTH_TOKEN."
            }

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
            twiml = f"<Response><Say voice='Polly.Aditi'>{message}</Say><Gather input='speech' timeout='5' action='/api/voice/ivr'><Say>You can give me a new command now.</Say></Gather></Response>"
            
            data = urllib.parse.urlencode({
                "To": self.phone,
                "From": TWILIO_FROM_NUMBER,
                "Twiml": twiml,
            }).encode("utf-8")

            req = urllib.request.Request(url, data=data, method="POST")
            auth_header = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode("latin1")
            import base64
            req.add_header("Authorization", f"Basic {base64.b64encode(auth_header).decode('ascii')}")

            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                logger.info("Call placed to %s (SID: %s)", self.phone, res.get("sid"))
                return {"success": True, "call_sid": res.get("sid"), "status": res.get("status")}
        except Exception as exc:
            logger.error("Failed to place voice call: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── SMS Notification ───────────────────────────────────────────────────────

    def send_sms(self, message: str) -> dict[str, Any]:
        """Send SMS notification to Avi's phone."""
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
            logger.info("Twilio SMS credentials missing. Falling back to email.")
            return {"success": False, "reason": "Twilio not configured."}

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
            data = urllib.parse.urlencode({
                "To": self.phone,
                "From": TWILIO_FROM_NUMBER,
                "Body": f"[VICY AI ALERT] {message}",
            }).encode("utf-8")

            req = urllib.request.Request(url, data=data, method="POST")
            auth_header = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode("latin1")
            import base64
            req.add_header("Authorization", f"Basic {base64.b64encode(auth_header).decode('ascii')}")

            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                logger.info("SMS dispatched to %s", self.phone)
                return {"success": True, "sid": res.get("sid")}
        except Exception as exc:
            logger.error("Failed to send SMS: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Email Notification ─────────────────────────────────────────────────────

    def send_email(self, subject: str, content_text: str, content_html: str = "") -> dict[str, Any]:
        """Send full report and task results to Avi's email."""
        if not (SMTP_USER and SMTP_PASS):
            logger.info("SMTP_USER/PASS not configured. Logging notification: %s - %s", subject, content_text[:100])
            return {
                "success": False,
                "reason": "SMTP credentials not provided in environment.",
                "logged": True,
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[VICY AI] {subject}"
            msg["From"] = SMTP_USER
            msg["To"] = self.email

            msg.attach(MIMEText(content_text, "plain"))
            if content_html:
                msg.attach(MIMEText(content_html, "html"))

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, self.email, msg.as_string())

            logger.info("Email notification sent successfully to %s", self.email)
            return {"success": True, "recipient": self.email}
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Orchestrated Dispatcher ────────────────────────────────────────────────

    def notify_task_complete(self, task_name: str, result_summary: str, pc_is_online: bool) -> dict[str, Any]:
        """
        Dispatches notification based on power status:
          - If PC is ON: Local Voice/Toast.
          - If PC is OFF: Phone Call -> SMS -> Email.
        """
        outcomes: dict[str, Any] = {"pc_is_online": pc_is_online}

        if pc_is_online:
            try:
                from tts_module import speak
                speak(f"Avi, your task {task_name} has completed.")
                outcomes["local_tts"] = True
            except Exception:
                outcomes["local_tts"] = False
            return outcomes

        # PC is OFF — Cloud Escalation Routine
        msg_short = f"Avi, your task '{task_name}' has completed successfully on your cloud computer."
        
        # 1. Voice Call
        call_res = self.place_voice_call(msg_short)
        outcomes["voice_call"] = call_res

        # 2. SMS (if call unconfigured or fallback)
        sms_res = self.send_sms(f"{msg_short} Output: {result_summary[:120]}")
        outcomes["sms"] = sms_res

        # 3. Email full report
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #0a0e17; color: #e2e8f0; padding: 20px;">
            <div style="border: 1px solid #00ffcc; border-radius: 8px; padding: 20px; background: #121824;">
                <h2 style="color: #00ffcc;">⚡ VICY 24/7 Cloud Task Complete</h2>
                <p>Hello <strong>Avi</strong>,</p>
                <p>Your task <strong>{task_name}</strong> was executed on your 24/7 autonomous cloud computer while your desktop was offline.</p>
                <hr style="border-color: #334155;"/>
                <h3>Output & Summary:</h3>
                <pre style="background: #040608; border: 1px solid #1e293b; padding: 12px; border-radius: 4px; color: #38bdf8; overflow-x: auto;">
{result_summary}
                </pre>
                <p style="margin-top: 20px;">
                    <a href="https://vicy-autonomous-ai.onrender.com" style="background: #ff007f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                        Open Cloud Mission Control
                    </a>
                </p>
            </div>
        </body>
        </html>
        """
        email_res = self.send_email(f"Task Completed: {task_name}", f"{msg_short}\n\nOutput:\n{result_summary}", html_body)
        outcomes["email"] = email_res

        return outcomes
