import re

with open('autonomous_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

with open('new_prompt.txt', 'r', encoding='utf-8') as f:
    new_prompt_body = f.read().strip()

# Replace SYSTEM_PROMPT block
pattern = r'SYSTEM_PROMPT = """.*?""".strip\(\)'
new_block = 'SYSTEM_PROMPT = """\n' + new_prompt_body + '\n""".strip()'
new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)
assert 'DO NOT ask' in new_content, "Prompt not replaced!"

# Add notify_telegram + notify_push handlers before chat_response
old_chat = '        elif act == "chat_response":\n            return {"action": act, "reply": action.get("reply", "")}'

new_handlers = (
    '        elif act == "notify_telegram":\n'
    '            try:\n'
    '                import notifier as N\n'
    '                msg   = action.get("message", "VICY alert")\n'
    '                title = action.get("title", "VICY")\n'
    '                t = N.send_telegram_text(msg, title)\n'
    '                v = N.send_telegram_voice(msg)\n'
    '                reply = "Avi, sent you a Telegram voice note + message! Check @VICYavi_bot."\n'
    '            except Exception as e:\n'
    '                reply = "Telegram error: " + str(e)\n'
    '            return {"action": act, "reply": reply}\n'
    '\n'
    '        elif act == "notify_push":\n'
    '            try:\n'
    '                import notifier as N\n'
    '                ok = N.send_push(action.get("message","VICY alert"), action.get("title","VICY"))\n'
    '                reply = "Push notification sent to Avi phone!"\n'
    '            except Exception as e:\n'
    '                reply = "Push error: " + str(e)\n'
    '            return {"action": act, "reply": reply}\n'
    '\n'
    '        elif act == "chat_response":\n'
    '            return {"action": act, "reply": action.get("reply", "")}'
)

new_content = new_content.replace(old_chat, new_handlers)
assert 'notify_telegram' in new_content, "Handler not added!"

with open('autonomous_agent.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

# Verify all patches
checks = {
    'notify_telegram handler': 'notify_telegram' in new_content,
    'notify_push handler':     'notify_push' in new_content,
    'DO NOT ask in prompt':    'DO NOT ask' in new_content,
    'VICYavi_bot identity':    '@VICYavi_bot' in new_content,
    'send_telegram_text call': 'send_telegram_text' in new_content,
    'send_telegram_voice call':'send_telegram_voice' in new_content,
}
print('\n=== PATCH RESULTS ===')
for k, v in checks.items():
    print(f'  {"OK" if v else "FAIL"} {k}')
print('\nAll good!' if all(checks.values()) else '\nSOME FAILED - CHECK!')
