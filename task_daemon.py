"""
task_daemon.py — Autonomous Background Scheduler & Asynchronous Worker.

Enables the AI to work on tasks in the background 24/7 inside its Docker computer:
  - Recurring tasks (hourly, daily, interval-based)
  - Long-running asynchronous jobs
  - Persistent task state saved in data/tasks.json
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:
    BackgroundScheduler = None
    IntervalTrigger = None

logger = logging.getLogger(__name__)

TASKS_DB_PATH = Path(os.environ.get("TASKS_DB_PATH", "/app/data/tasks.json")).resolve()


class TaskDaemon:
    """Manages autonomous, recurring, and background tasks inside the container."""

    def __init__(self, execute_callback: Callable[[str], Any] | None = None) -> None:
        self.execute_callback = execute_callback
        self.tasks: dict[str, dict[str, Any]] = {}
        if BackgroundScheduler:
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            logger.info("TaskDaemon started with APScheduler.")
        else:
            self.scheduler = None
            logger.info("APScheduler not present; background threading available.")
        self._load_tasks()

    def _load_tasks(self) -> None:
        """Load registered tasks from persistent JSON."""
        try:
            if TASKS_DB_PATH.exists():
                with open(TASKS_DB_PATH, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                logger.info("Loaded %d scheduled tasks from %s", len(self.tasks), TASKS_DB_PATH)
                for task_id, info in self.tasks.items():
                    if info.get("active", True) and info.get("interval_minutes"):
                        self._schedule_interval(task_id, info["interval_minutes"], info["instruction"])
            else:
                TASKS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                self._save_tasks()
        except Exception as exc:
            logger.warning("Could not load tasks from %s: %s", TASKS_DB_PATH, exc)

    def _save_tasks(self) -> None:
        """Persist tasks to disk."""
        try:
            TASKS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TASKS_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as exc:
            logger.error("Could not save tasks: %s", exc)

    def _schedule_interval(self, task_id: str, minutes: int, instruction: str) -> None:
        """Add an interval trigger to APScheduler."""
        def job():
            logger.info("Running scheduled autonomous task [%s]: %s", task_id, instruction)
            if self.execute_callback:
                try:
                    result = self.execute_callback(instruction)
                    self.record_task_run(task_id, result)
                except Exception as e:
                    logger.error("Error executing scheduled task %s: %s", task_id, e)
                    self.record_task_run(task_id, {"error": str(e)})

        if self.scheduler and IntervalTrigger:
            self.scheduler.add_job(
                job,
                trigger=IntervalTrigger(minutes=minutes),
                id=task_id,
                replace_existing=True,
            )

    def add_scheduled_task(self, name: str, instruction: str, interval_minutes: int) -> dict[str, Any]:
        """Register a new recurring autonomous task."""
        task_id = f"task_{int(time.time())}_{name.lower().replace(' ', '_')}"
        info = {
            "id": task_id,
            "name": name,
            "instruction": instruction,
            "interval_minutes": interval_minutes,
            "created_at": datetime.datetime.now().isoformat(),
            "last_run": None,
            "active": True,
            "run_count": 0,
            "last_result": None,
        }
        self.tasks[task_id] = info
        self._schedule_interval(task_id, interval_minutes, instruction)
        self._save_tasks()
        return info

    def run_async_task(self, name: str, instruction: str) -> str:
        """Launch a long-running one-shot task in a background worker thread."""
        task_id = f"async_{int(time.time())}_{name.lower().replace(' ', '_')}"
        self.tasks[task_id] = {
            "id": task_id,
            "name": name,
            "instruction": instruction,
            "status": "running",
            "started_at": datetime.datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
        }
        self._save_tasks()

        def worker():
            logger.info("Starting background async task [%s]: %s", task_id, instruction)
            try:
                res = self.execute_callback(instruction) if self.execute_callback else "No callback"
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["completed_at"] = datetime.datetime.now().isoformat()
                self.tasks[task_id]["result"] = res
            except Exception as e:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(e)
            self._save_tasks()

        threading.Thread(target=worker, daemon=True).start()
        return task_id

    def record_task_run(self, task_id: str, result: Any) -> None:
        """Update last run time and stats."""
        if task_id in self.tasks:
            self.tasks[task_id]["last_run"] = datetime.datetime.now().isoformat()
            self.tasks[task_id]["run_count"] = self.tasks[task_id].get("run_count", 0) + 1
            self.tasks[task_id]["last_result"] = str(result)[:500]
            self._save_tasks()

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return all registered tasks."""
        return list(self.tasks.values())

    def remove_task(self, task_id: str) -> bool:
        """Remove a task."""
        if task_id in self.tasks:
            try:
                self.scheduler.remove_job(task_id)
            except Exception:
                pass
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False
