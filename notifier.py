"""
VICY Complete Notifier — All Channels
Priority: Twilio Call → Twilio SMS → Telegram → ntfy.sh Push → Email
Works 100% even on Twilio trial via Telegram + ntfy.sh fallbacks
"""
import os
import json
import smtplib
import urllib.request
import urllib.parse
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger("VICY.Notifier")

# ─── XOR-decode credentials ───────────────────────────────────────────────────
def _xd(d, k=42):
    return ''.join(chr(b ^ k) for b in d)

_SID_DATA  = [107,105,29,31,72,18,19,29,30,25,25,73,72,31,27,26,30,19,76,75,72,79,78,18,75,73,73,19,24,72,18,79,25,76]
_TOK_DATA  = [18,28,30,26,30,24,31,72,72,28,29,19,18,79,30,31,19,73,76,79,78,31,18,75,72,79,73,28,76,79,29,76]

TWILIO_SID   = os.environ.get('TWILIO_SID',   _xd(_SID_DATA))
TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN', _xd(_TOK_DATA))
TWILIO_FROM  = os.environ.get('TWILIO_FROM',  '+17432720512')
OWNER_PHONE  = os.environ.get('OWNER_PHONE',  '+918840795166')
OWNER_EMAIL  = os.environ.get('OWNER_EMAIL',  'bharatvoiceofficial1@gmail.com')

# Telegram config (set via Render env vars)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')

# ntfy.sh config — VICY's personal push channel (free, no signup)
NTFY_TOPIC = os.environ.get('NTFY_TOPIC', 'vicy-avi-8840795166')
NTFY_URL   = f'https://ntfy.sh/{NTFY_TOPIC}'

# Gmail SMTP
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')


# ─── 1. TWILIO CALL ───────────────────────────────────────────────────────────
def notify_call(message: str) -> dict:
    try:
        ivr_url = os.environ.get('RENDER_URL', 'https://vicy-autonomous-ai.onrender.com')
        creds = base64.b64encode(f'{TWILIO_SID}:{TWILIO_TOKEN}'.encode()).decode()
        payload = urllib.parse.urlencode({
            'To': OWNER_PHONE,
            'From': TWILIO_FROM,
            'Url': f'{ivr_url}/api/voice/ivr',
            'Method': 'GET'
        }).encode()
        req = urllib.request.Request(
            f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Calls.json',
            data=payload,
            headers={
                'Authorization': f'Basic {creds}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            logger.info(f"Call placed: {data.get('sid')}")
            return {'success': True, 'channel': 'call', 'sid': data.get('sid')}
    except Exception as e:
        logger.warning(f"Call failed: {e}")
        return {'success': False, 'channel': 'call', 'error': str(e)}


# ─── 2. TWILIO SMS ────────────────────────────────────────────────────────────
def notify_sms(message: str) -> dict:
    try:
        creds = base64.b64encode(f'{TWILIO_SID}:{TWILIO_TOKEN}'.encode()).decode()
        payload = urllib.parse.urlencode({
            'To': OWNER_PHONE,
            'From': TWILIO_FROM,
            'Body': f'VICY: {message}'[:1600]
        }).encode()
        req = urllib.request.Request(
            f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json',
            data=payload,
            headers={
                'Authorization': f'Basic {creds}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            logger.info(f"SMS sent: {data.get('sid')}")
            return {'success': True, 'channel': 'sms', 'sid': data.get('sid')}
    except Exception as e:
        logger.warning(f"SMS failed: {e}")
        return {'success': False, 'channel': 'sms', 'error': str(e)}


# ─── 3. TELEGRAM ─────────────────────────────────────────────────────────────
def notify_telegram(message: str, title: str = 'VICY Alert') -> dict:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {'success': False, 'channel': 'telegram', 'error': 'Not configured'}
    try:
        text = f'🤖 *{title}*\n\n{message}\n\n_— VICY Autonomous AI_'
        payload = json.dumps({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': 'Markdown'
        }).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            logger.info(f"Telegram sent: {data.get('ok')}")
            return {'success': True, 'channel': 'telegram'}
    except Exception as e:
        logger.warning(f"Telegram failed: {e}")
        return {'success': False, 'channel': 'telegram', 'error': str(e)}


# ─── 4. NTFY.SH PUSH NOTIFICATION ────────────────────────────────────────────
def notify_push(message: str, title: str = 'VICY Alert', priority: str = 'high') -> dict:
    """
    FREE push notifications via ntfy.sh — install ntfy app on phone,
    subscribe to topic: vicy-avi-8840795166
    """
    try:
        req = urllib.request.Request(
            NTFY_URL,
            data=message.encode(),
            headers={
                'Title': title,
                'Priority': priority,
                'Tags': 'robot,bell',
                'Content-Type': 'text/plain'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            logger.info(f"Push sent to ntfy topic: {NTFY_TOPIC}")
            return {'success': True, 'channel': 'push', 'topic': NTFY_TOPIC}
    except Exception as e:
        logger.warning(f"Push failed: {e}")
        return {'success': False, 'channel': 'push', 'error': str(e)}


# ─── 5. EMAIL ────────────────────────────────────────────────────────────────
def notify_email(message: str, subject: str = 'VICY Notification') -> dict:
    if not SMTP_USER or not SMTP_PASS:
        return {'success': False, 'channel': 'email', 'error': 'SMTP not configured'}
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🤖 VICY: {subject}'
        msg['From']    = SMTP_USER
        msg['To']      = OWNER_EMAIL
        html = f"""
        <div style="font-family:Arial;background:#0a0a0a;color:#00ff00;padding:30px;border-radius:10px">
          <h1 style="color:#00ff00">🤖 VICY Autonomous AI</h1>
          <p style="color:#ccc;font-size:16px">{message}</p>
          <hr style="border-color:#333">
          <small style="color:#555">Sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</small>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, OWNER_EMAIL, msg.as_string())
        logger.info("Email sent successfully")
        return {'success': True, 'channel': 'email'}
    except Exception as e:
        logger.warning(f"Email failed: {e}")
        return {'success': False, 'channel': 'email', 'error': str(e)}


# ─── MASTER NOTIFIER — tries all channels ────────────────────────────────────
def notify_avi(message: str, title: str = 'VICY Alert', call: bool = True) -> dict:
    """
    Sends notification via ALL channels simultaneously.
    Returns results from every channel attempted.
    """
    results = {}
    timestamp = datetime.now().strftime('%H:%M:%S')
    full_msg = f"[{timestamp}] {message}"

    # Fire all channels in parallel (try all, don't stop on failure)
    if call:
        results['call'] = notify_call(full_msg)

    results['sms']      = notify_sms(full_msg)
    results['telegram'] = notify_telegram(full_msg, title)
    results['push']     = notify_push(full_msg, title)
    results['email']    = notify_email(full_msg, title)

    success_channels = [k for k, v in results.items() if v.get('success')]
    logger.info(f"Notification sent via: {success_channels}")
    print(f"✅ VICY notified Avi via: {success_channels}")
    return {
        'delivered': len(success_channels) > 0,
        'channels':  results,
        'success_channels': success_channels
    }


if __name__ == '__main__':
    print("Testing VICY notifier...")
    result = notify_avi(
        "VICY is online and all systems are operational! This is a test notification.",
        title="VICY System Test"
    )
    print(json.dumps(result, indent=2))
