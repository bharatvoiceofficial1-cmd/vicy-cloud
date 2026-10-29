import re

with open('autonomous_agent.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Find and fix the weak fallback reply
old_fallback = ('        return {"action": "chat_response", '
                '"reply": f"Hello Avi, I am online in your autonomous '
                '24/7 cloud computer. Ready for your instructions."}')

new_fallback = '''        # Smart keyword fallbacks
        if "fetch" in lower or ("http" in lower and "scrape" not in lower):
            m = re.search(r"https?://[^\\s]+", instruction)
            url = m.group(0) if m else "https://httpbin.org/json"
            return {"action": "fetch_web", "url": url}

        if ("notify" in lower or "message me" in lower or "alert me" in lower) and ("telegram" in lower or "send" in lower):
            clean = re.sub(r"notify( me)?( on)?( telegram)?|send( me)?|alert( me)?", "", instruction, flags=re.I).strip()
            return {"action": "notify_telegram", "message": clean or "VICY notification", "title": "VICY Alert"}

        if "push" in lower or "ntfy" in lower:
            return {"action": "notify_push", "message": instruction, "title": "VICY"}

        if "system" in lower or ("status" in lower and "website" not in lower):
            return {"action": "system_status"}

        return {"action": "chat_response", "reply": f"Hello Avi! Processing your request: {instruction[:120]}"}'''

if old_fallback in src:
    src = src.replace(old_fallback, new_fallback)
    print("Replaced fallback!")
else:
    # Try to find it
    idx = src.find('Ready for your instructions')
    if idx > -1:
        start = src.rfind('\n        return', 0, idx)
        end = idx + src[idx:].index('}') + 1
        print(f"Found at {start}-{end}:")
        print(repr(src[start:end]))
    else:
        print("Not found - checking all return statements in fallback area")
        idx2 = src.find('3. Fast Rule Fallback')
        print(src[idx2:idx2+600])

with open('autonomous_agent.py', 'w', encoding='utf-8') as f:
    f.write(src)
print("Done. notify_telegram in src:", "notify_telegram" in src)
print("fetch_web fallback in src:", "fetch_web" in src and "fetch" in src)
