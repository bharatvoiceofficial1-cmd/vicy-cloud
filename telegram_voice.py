"""
VICY Telegram Voice Message Sender
Converts text to speech and sends as voice note on Telegram
"""
import urllib.request
import urllib.parse
import json
import os
import tempfile
from gtts import gTTS

TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '9077942044:AAFAcKAc7aiSHiTRuW7YFSHociRC2BozdVY')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID',   '8591652039')


def send_voice_message(text: str, lang: str = 'en') -> dict:
    """Generate TTS audio and send as Telegram voice message."""
    # Generate speech
    tts = gTTS(text=text, lang=lang, slow=False)
    tmp = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False)
    tmp.close()
    tts.save(tmp.name)

    # Send via Telegram sendVoice API
    boundary = '----VICYBoundary7MA4YWxkTrZu0gW'
    with open(tmp.name, 'rb') as f:
        audio_data = f.read()

    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f'{CHAT_ID}\r\n'
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="voice"; filename="vicy.ogg"\r\n'
        f'Content-Type: audio/ogg\r\n\r\n'
    ).encode('utf-8') + audio_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

    req = urllib.request.Request(
        f'https://api.telegram.org/bot{TOKEN}/sendVoice',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            return {'success': result.get('ok'), 'channel': 'telegram_voice'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        os.unlink(tmp.name)


def send_text_message(text: str) -> dict:
    """Send plain text message on Telegram."""
    payload = json.dumps({'chat_id': CHAT_ID, 'text': text}).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json; charset=utf-8'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        return {'success': data.get('ok'), 'channel': 'telegram_text'}


def notify_avi_voice(message: str):
    """Send both voice + text message to Avi on Telegram."""
    print(f'Sending voice message: {message[:60]}...')
    voice_result = send_voice_message(message)
    text_result  = send_text_message(f'VICY: {message}')
    return {'voice': voice_result, 'text': text_result}


if __name__ == '__main__':
    result = notify_avi_voice(
        'Hello Avi! This is VICY, your autonomous AI assistant. '
        'I am now sending you voice messages directly on Telegram. '
        'Every time I finish a task, I will speak the result to you. '
        'VICY is fully operational!'
    )
    print('Result:', result)
