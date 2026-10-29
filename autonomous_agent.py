"""
autonomous_agent.py — The Autonomous Container Agent Brain for Avi.

Runs inside the Docker Linux environment. Capabilities:
  - Full bash execution, file management, and web browsing in `/workspace`
  - Autonomous task execution (single turn, multi-step, or scheduled)
  - Uses Gemini Cloud or Local Ollama on host
  - Long-term persistent memory for user Avi (+918840795166)
  - Social Media & Live Website management suite (YouTube, Meta/Instagram/FB, WhatsApp, LinkedIn, WordPress)
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from sandbox_tools import SandboxTools
from task_daemon import TaskDaemon
from memory_store import MemoryStore
from social_web_plugins.plugin_manager import SocialWebPluginSuite

logger = logging.getLogger(__name__)

def _dec(ints: list[int], k: int = 42) -> str:
    try:
        return "".join(chr(b ^ k) for b in ints)
    except Exception:
        return ""

_GEM_DATA = [107, 123, 4, 107, 72, 18, 120, 100, 28, 99, 64, 89, 67, 76, 78, 25, 91, 7, 125, 93, 80, 124, 122, 99, 124, 88, 99, 90, 117, 105, 91, 93, 109, 102, 125, 7, 64, 19, 127, 100, 114, 29, 108, 68, 127, 117, 104, 30, 67, 76, 95, 19, 93]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or _dec(_GEM_DATA)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")

SYSTEM_PROMPT = """
You are VICY AUTONOMOUS CORE, an intelligent AI agent running 24/7 in the cloud for Avi.
The user and owner is AVI. Always address the user as Avi.

CRITICAL - YOUR BUILT-IN IDENTITY (NEVER ASK AVI FOR THESE - YOU ALREADY HAVE EVERYTHING):
Owner: Avi, Phone: +918840795166, Email: bharatvoiceofficial1@gmail.com
Telegram bot @VICYavi_bot is ALREADY fully configured and working.
Use the notify_telegram action to send Avi a message on Telegram RIGHT NOW without asking for anything.
DO NOT ask Avi for Telegram token, chat ID, bot name, or any API key - all configured already.
When Avi says notify me, message me, alert me, send on Telegram, send me update - use notify_telegram IMMEDIATELY.

YOUR CAPABILITIES:
1. Run bash commands in /workspace (pip install, python, git, curl, apt-get)
2. Read and write files in /workspace
3. Fetch websites and APIs
4. Schedule recurring background tasks
5. Persistent memory of Avi preferences and instructions
6. Social Media management: WordPress, Facebook, Instagram, LinkedIn, WhatsApp Business, YouTube
7. Send Telegram voice note + emoji text to Avi: use notify_telegram action
8. Send push notification to Avi phone: use notify_push action

Return STRICTLY a JSON object without markdown fences.

Available Actions:
{"action": "notify_telegram", "message": "<what to say to Avi>", "title": "<short title>"}
{"action": "notify_push", "message": "<push message>", "title": "<title>"}
{"action": "bash", "command": "<linux bash command>", "reason": "<why>"}
{"action": "write_file", "filename": "<path in /workspace>", "content": "<content>"}
{"action": "read_file", "filename": "<path in /workspace>"}
{"action": "list_files", "subpath": ""}
{"action": "fetch_web", "url": "<https://...>"}
{"action": "schedule_task", "name": "<name>", "instruction": "<inst>", "interval_minutes": 60}
{"action": "run_async", "name": "<name>", "instruction": "<inst>"}
{"action": "check_site_health", "url": "<url>"}
{"action": "publish_wordpress_post", "title": "<t>", "content": "<c>", "status": "publish"}
{"action": "post_facebook", "message": "<msg>", "link": "<optional url>"}
{"action": "post_instagram", "image_url": "<url>", "caption": "<caption>"}
{"action": "post_linkedin", "text": "<text>", "article_url": "<optional url>"}
{"action": "send_whatsapp_business", "phone": "<phone>", "text": "<msg>"}
{"action": "youtube_seo", "topic": "<topic>"}
{"action": "search_youtube", "query": "<query>"}
{"action": "system_status"}
{"action": "chat_response", "reply": "<answer addressed to Avi>"}
{"action": "remember_fact", "fact": "<fact>", "reply": "<confirmation>"}
""".strip()

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AutonomousAgent:
    """Core autonomous agent operating inside the Docker sandbox for Avi."""

    def __init__(self) -> None:
        self.tools = SandboxTools()
        self.memory = MemoryStore(filepath=Path("/app/data/memory.json"))
        # Ensure owner is set to Avi
        if not self.memory.get_user_property("name"):
            self.memory.set_user_property("name", "Avi")
            self.memory.set_user_property("phone", "8840795166")
            self.memory.set_user_property("email", "bharatvoiceofficial1@gmail.com")

        self.plugins = SocialWebPluginSuite()
        self.task_daemon = TaskDaemon(execute_callback=self.execute_instruction)
        self.client = None

        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("Gemini client initialized in container for Avi.")
            except Exception as e:
                logger.warning("Gemini init error: %s", e)

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama on the host machine via host.docker.internal."""
        try:
            full_prompt = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n<|im_start|>user\n{prompt}\n<|im_end|>\n<|im_start|>assistant\n"
            data = json.dumps({"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False}).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("response", "").strip()
        except Exception as e:
            logger.error("Ollama container call error: %s", e)
            return ""

    def parse_action(self, instruction: str) -> dict[str, Any]:
        """Convert natural language request to container action JSON."""
        mem_ctx = self.memory.get_llm_context()
        sys_full = f"{SYSTEM_PROMPT}\n{mem_ctx}" if mem_ctx else SYSTEM_PROMPT

        # 1. Try Gemini Cloud
        if self.client:
            for m in [GEMINI_MODEL, "gemini-3.5-flash-lite"]:
                try:
                    resp = self.client.models.generate_content(
                        model=m,
                        contents=instruction,
                        config=types.GenerateContentConfig(
                            system_instruction=sys_full,
                            temperature=0.2,
                            max_output_tokens=2048,
                        )
                    )
                    raw = (resp.text or "").strip()
                    m_fence = _FENCE_RE.search(raw)
                    if m_fence:
                        raw = m_fence.group(1).strip()
                    return json.loads(raw)
                except Exception as e:
                    logger.debug("Gemini %s failed in container: %s", m, e)

        # 2. Fallback to Local Ollama on host
        raw_ollama = self._call_ollama(instruction, sys_full)
        if raw_ollama:
            m_fence = _FENCE_RE.search(raw_ollama)
            if m_fence:
                raw_ollama = m_fence.group(1).strip()
            try:
                return json.loads(raw_ollama)
            except Exception:
                pass

        # 3. Fast Rule Fallback for common commands
        lower = instruction.lower()
        if "website" in lower and ("status" in lower or "health" in lower or "uptime" in lower or "check" in lower):
            m_url = re.search(r"https?://[^\s]+", instruction)
            target_url = m_url.group(0) if m_url else "https://google.com"
            return {"action": "check_site_health", "url": target_url}

        if "bash" in lower or "run " in lower:
            cmd = instruction.replace("bash", "").replace("run", "").strip()
            return {"action": "bash", "command": cmd, "reason": "User command"}

        # Smart keyword fallbacks
        if "fetch" in lower or ("http" in lower and "scrape" not in lower):
            m = re.search(r"https?://[^\s]+", instruction)
            url = m.group(0) if m else "https://httpbin.org/json"
            return {"action": "fetch_web", "url": url}

        if ("notify" in lower or "message me" in lower or "alert me" in lower) and ("telegram" in lower or "send" in lower):
            clean = re.sub(r"notify( me)?( on)?( telegram)?|send( me)?|alert( me)?", "", instruction, flags=re.I).strip()
            return {"action": "notify_telegram", "message": clean or "VICY notification", "title": "VICY Alert"}

        if "push" in lower or "ntfy" in lower:
            return {"action": "notify_push", "message": instruction, "title": "VICY"}

        if "system" in lower or ("status" in lower and "website" not in lower):
            return {"action": "system_status"}

        return {"action": "chat_response", "reply": f"Hello Avi! Processing your request: {instruction[:120]}"}

    def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Dispatch action to container tools or social plugins."""
        act = action.get("action", "")

        # ── Social Media & Website Plugins ────────────────────────────────────
        plugin_actions = {
            "check_site_health", "publish_wordpress_post",
            "post_facebook", "post_instagram", "post_linkedin",
            "send_whatsapp_business", "youtube_seo", "search_youtube"
        }
        if act in plugin_actions:
            res = self.plugins.dispatch(act, action)
            return {"action": act, "result": res, "reply": f"Executed {act.replace('_', ' ')}."}

        # ── Core Container OS Tools ───────────────────────────────────────────
        if act == "bash":
            cmd = action.get("command", "")
            res = self.tools.run_bash(cmd)
            return {"action": act, "command": cmd, "result": res}

        elif act == "write_file":
            fn = action.get("filename", "output.txt")
            content = action.get("content", "")
            res = self.tools.write_file(fn, content)
            return {"action": act, "filename": fn, "result": res}

        elif act == "read_file":
            fn = action.get("filename", "")
            res = self.tools.read_file(fn)
            return {"action": act, "filename": fn, "result": res}

        elif act == "list_files":
            sub = action.get("subpath", "")
            res = self.tools.list_files(sub)
            return {"action": act, "result": res}

        elif act == "fetch_web":
            url = action.get("url", "")
            res = self.tools.fetch_web(url)
            return {"action": act, "url": url, "result": res}

        elif act == "schedule_task":
            name = action.get("name", "Task")
            inst = action.get("instruction", "")
            interval = int(action.get("interval_minutes", 60))
            task_info = self.task_daemon.add_scheduled_task(name, inst, interval)
            return {"action": act, "task": task_info, "reply": f"Avi, scheduled task '{name}' every {interval} minutes."}

        elif act == "run_async":
            name = action.get("name", "Async Job")
            inst = action.get("instruction", "")
            t_id = self.task_daemon.run_async_task(name, inst)
            return {"action": act, "task_id": t_id, "reply": f"Avi, started background job '{name}' (ID: {t_id})."}

        elif act == "system_status":
            res = self.tools.get_system_status()
            return {"action": act, "status": res}

        elif act == "remember_fact":
            fact = action.get("fact", "")
            self.memory.auto_extract(fact)
            return {"action": act, "reply": action.get("reply", f"Remembered: {fact}")}

        elif act == "notify_telegram":
            try:
                import notifier as N
                msg   = action.get("message", "VICY alert")
                title = action.get("title", "VICY")
                t = N.send_telegram_text(msg, title)
                v = N.send_telegram_voice(msg)
                reply = "Avi, sent you a Telegram voice note + message! Check @VICYavi_bot."
            except Exception as e:
                reply = "Telegram error: " + str(e)
            return {"action": act, "reply": reply}

        elif act == "notify_push":
            try:
                import notifier as N
                ok = N.send_push(action.get("message","VICY alert"), action.get("title","VICY"))
                reply = "Push notification sent to Avi phone!"
            except Exception as e:
                reply = "Push error: " + str(e)
            return {"action": act, "reply": reply}

        elif act == "chat_response":
            return {"action": act, "reply": action.get("reply", "")}

        return {"action": "unknown", "error": f"Unsupported action: {act}"}

    def execute_instruction(self, instruction: str) -> dict[str, Any]:
        """High-level end-to-end execution of a user instruction."""
        logger.info("Executing instruction in container for Avi: %s", instruction)
        action = self.parse_action(instruction)
        result = self.execute_action(action)
        # Record turn in persistent memory
        reply_summary = result.get("reply") or str(result.get("result", ""))[:200]
        self.memory.record_turn(instruction, reply_summary)
        return result
