"""
hybrid_orchestrator.py — Smart Execution Router & Escalation Workflow for Avi.

Workflow Logic:
  1. If PC is ON (Local Backend online):
     - Executes task locally or in local sandbox.
     - Notifies Avi on Desktop (Voice TTS + UI Log).
  2. If PC is OFF (Desktop powered down / shutdown):
     - Automatically routes task to 24/7 Cloud Render Container.
     - Executes in isolated Linux container.
     - Escalation Notification:
         Step 1: Phone call to Avi (+918840795166).
         Step 2: SMS notification.
         Step 3: Comprehensive Email report to bharatvoiceofficial1@gmail.com.
     - Interactive Phone Call: Avi can speak more commands directly over the phone!
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

from notifier import Notifier

logger = logging.getLogger(__name__)

LOCAL_AGENT_URL = os.environ.get("LOCAL_AGENT_URL", "http://127.0.0.1:8008")
CLOUD_AGENT_URL = os.environ.get("CLOUD_AGENT_URL", "https://vicy-autonomous-ai.onrender.com")


class HybridOrchestrator:
    """Intelligently balances workloads between Local PC and 24/7 Cloud."""

    def __init__(self) -> None:
        self.notifier = Notifier()

    def is_local_pc_online(self) -> bool:
        """Ping local PC assistant backend to see if desktop is powered on."""
        try:
            req = urllib.request.Request(f"{LOCAL_AGENT_URL}/", headers={"User-Agent": "VICY-Orchestrator/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def execute_and_notify(self, task_name: str, instruction: str) -> dict[str, Any]:
        """
        Executes instruction on appropriate node and alerts Avi through
        the designated channel based on desktop power status.
        """
        pc_online = self.is_local_pc_online()
        logger.info("Task: '%s' | Local PC Online: %s", task_name, pc_online)

        result_data: dict[str, Any] = {}

        if pc_online:
            # ── 1. Desktop is ON: Execute locally ────────────────────────────
            try:
                data = json.dumps({"instruction": instruction}).encode("utf-8")
                req = urllib.request.Request(f"{LOCAL_AGENT_URL}/api/instruct", data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    result_data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.warning("Local execution failed, failing over to Cloud: %s", e)
                pc_online = False

        if not pc_online:
            # ── 2. Desktop is OFF: Execute on 24/7 Cloud Core ───────────────
            logger.info("Desktop powered off. Routing task '%s' to 24/7 Cloud Core...", task_name)
            try:
                data = json.dumps({"instruction": instruction}).encode("utf-8")
                req = urllib.request.Request(f"{CLOUD_AGENT_URL}/api/instruct", data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as resp:
                    result_data = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                result_data = {"error": f"Cloud execution error: {exc}"}

        # ── 3. Notification Escalation ───────────────────────────────────────
        summary = str(result_data.get("reply") or result_data.get("result") or result_data)[:500]
        notify_res = self.notifier.notify_task_complete(
            task_name=task_name,
            result_summary=summary,
            pc_is_online=pc_online
        )

        return {
            "task_name": task_name,
            "executed_on": "local_desktop" if pc_online else "cloud_render_container",
            "result": result_data,
            "notifications": notify_res,
        }
