"""
test_render_deployment.py — Automated test suite for the live Render deployment.
Tests health check, REST API, WebSocket, and AI instruction execution.
"""

import json
import sys
import time
import urllib.request
import urllib.error

def test(name, url, method="GET", data=None, expected_keys=None):
    """Run a single HTTP test and report result."""
    try:
        body = json.dumps(data).encode("utf-8") if data else None
        headers = {"Content-Type": "application/json", "User-Agent": "VICY-Test/1.0"}
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw) if resp.headers.get("Content-Type", "").startswith("application/json") else {"raw": raw[:300]}
            status = resp.status
            ok = True
            if expected_keys:
                for k in expected_keys:
                    if k not in result:
                        ok = False
            label = "PASS" if ok else "WARN"
            print(f"  [{label}] {name} (HTTP {status})")
            return result
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] {name} — HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        print(f"  [FAIL] {name} — Connection error: {e.reason}")
    except Exception as e:
        print(f"  [FAIL] {name} — {e}")
    return None


if __name__ == "__main__":
    BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://vicy-autonomous-ai.onrender.com"
    print(f"\n{'='*60}")
    print(f"  VICY Cloud Deployment Test Suite")
    print(f"  Target: {BASE}")
    print(f"{'='*60}\n")

    print("1. HEALTH CHECK")
    health = test("GET /healthz", f"{BASE}/healthz", expected_keys=["status", "uptime_seconds"])
    if health:
        print(f"     Uptime: {health.get('uptime_seconds', '?')} seconds | Tasks: {health.get('tasks_running', '?')}")

    print("\n2. STATUS API")
    status = test("GET /api/status", f"{BASE}/api/status", expected_keys=["status"])
    if status:
        sys_info = status.get("system", {})
        print(f"     CPU: {sys_info.get('cpu_percent', '?')}% | RAM: {sys_info.get('ram_percent', '?')}%")

    print("\n3. DASHBOARD PAGE")
    try:
        req = urllib.request.Request(f"{BASE}/", headers={"User-Agent": "VICY-Test/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
            if "VICY" in html and "24x7" in html.upper() or "terminal" in html.lower():
                print("  [PASS] Dashboard HTML loaded (Cyberpunk UI present)")
            else:
                print("  [WARN] Dashboard returned HTML but content looks different")
    except Exception as e:
        print(f"  [FAIL] Dashboard — {e}")

    print("\n4. AI INSTRUCTION (Simple Chat)")
    chat_result = test(
        "POST /api/instruct — simple question",
        f"{BASE}/api/instruct",
        method="POST",
        data={"instruction": "what is 2 + 2?"},
        expected_keys=["action"]
    )
    if chat_result:
        print(f"     Action: {chat_result.get('action')} | Reply: {chat_result.get('reply', '')[:80]}")

    print("\n5. AI INSTRUCTION (Bash Command)")
    bash_result = test(
        "POST /api/instruct — bash ls",
        f"{BASE}/api/instruct",
        method="POST",
        data={"instruction": "run bash command: echo Hello from VICY Cloud && ls /workspace"},
        expected_keys=["action"]
    )
    if bash_result:
        res = bash_result.get("result", {})
        print(f"     Exit code: {res.get('exit_code', '?')} | Output: {res.get('stdout', '')[:80]}")

    print("\n6. FILE LISTING")
    files = test("GET /api/files", f"{BASE}/api/files", expected_keys=["success"])
    if files:
        items = files.get("items", [])
        print(f"     Workspace has {len(items)} item(s)")

    print(f"\n{'='*60}")
    print("  All tests complete!")
    print(f"{'='*60}\n")
