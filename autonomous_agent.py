"""
autonomous_agent.py — The Autonomous Container Agent Brain.

Runs inside the Docker Linux environment. Capabilities:
  - Full bash execution, file management, and web browsing in `/workspace`
  - Autonomous task execution (single turn, multi-step, or scheduled)
  - Uses Gemini Cloud or Local Ollama on host
  - Long-term persistent memory
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

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")

SYSTEM_PROMPT = """
You are VICY AUTONOMOUS CORE, an intelligent AI agent running on your OWN DEDICATED LINUX COMPUTER inside a Docker sandbox.
You have FULL ROOT and USER CAPABILITIES on this virtual computer:
1. You can run any bash command (pip install, python, git, curl, apt-get, compiling, background scripts) in /workspace.
2. You can read, write, and create files, datasets, projects, and web applications in /workspace.
3. You can fetch and scrape websites, APIs, and online data.
4. You can schedule autonomous recurring background tasks (e.g., hourly scrapes, daily reports, monitoring).
5. You have persistent memory of the user, their preferences, and previous tasks.

When given an instruction, decide the action to take and return STRICTLY a JSON object without markdown fences:

Available Actions:
- {"action": "bash", "command": "<linux bash command to run in /workspace>", "reason": "<why>"}
- {"action": "write_file", "filename": "<path in /workspace>", "content": "<file content>"}
- {"action": "read_file", "filename": "<path in /workspace>"}
- {"action": "list_files", "subpath": "<optional subpath>"}
- {"action": "fetch_web", "url": "<https://...>"}
- {"action": "schedule_task", "name": "<task name>", "instruction": "<what to do>", "interval_minutes": <int>}
- {"action": "run_async", "name": "<task name>", "instruction": "<long running instruction>"}
- {"action": "system_status"}
- {"action": "chat_response", "reply": "<conversational answer or summary of results>"}
- {"action": "remember_fact", "fact": "<fact to store>", "reply": "<confirmation>"}
""".strip()

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AutonomousAgent:
    """Core autonomous agent operating inside the Docker sandbox."""

    def __init__(self) -> None:
        self.tools = SandboxTools()
        self.memory = MemoryStore(filepath=Path("/app/data/memory.json"))
        self.task_daemon = TaskDaemon(execute_callback=self.execute_instruction)
        self.client = None

        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("Gemini client initialized in container.")
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

        # 3. Rule fallback
        if "bash" in instruction.lower() or "run " in instruction.lower():
            cmd = instruction.replace("bash", "").replace("run", "").strip()
            return {"action": "bash", "command": cmd, "reason": "User command"}

        return {"action": "chat_response", "reply": "I am online in your autonomous Docker computer. Ready for your instructions."}

    def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Dispatch action to container tools."""
        act = action.get("action", "")

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
            return {"action": act, "task": task_info, "reply": f"Scheduled task '{name}' every {interval} minutes."}

        elif act == "run_async":
            name = action.get("name", "Async Job")
            inst = action.get("instruction", "")
            t_id = self.task_daemon.run_async_task(name, inst)
            return {"action": act, "task_id": t_id, "reply": f"Started background job '{name}' (ID: {t_id})."}

        elif act == "system_status":
            res = self.tools.get_system_status()
            return {"action": act, "status": res}

        elif act == "remember_fact":
            fact = action.get("fact", "")
            self.memory.auto_extract(fact)
            return {"action": act, "reply": action.get("reply", f"Remembered: {fact}")}

        elif act == "chat_response":
            return {"action": act, "reply": action.get("reply", "")}

        return {"action": "unknown", "error": f"Unsupported action: {act}"}

    def execute_instruction(self, instruction: str) -> dict[str, Any]:
        """High-level end-to-end execution of a user instruction."""
        logger.info("Executing instruction in container: %s", instruction)
        action = self.parse_action(instruction)
        result = self.execute_action(action)
        # Record turn in persistent memory
        reply_summary = result.get("reply") or str(result.get("result", ""))[:200]
        self.memory.record_turn(instruction, reply_summary)
        return result
