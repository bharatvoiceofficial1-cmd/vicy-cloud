"""
sandbox_tools.py — Autonomous OS Capabilities for the Containerized AI.

Provides the agent with its own Linux computer capabilities:
  - Full bash execution (`/bin/bash`) in `/workspace`
  - File reading, writing, editing, and listing
  - Web scraping & HTTP requests
  - Hardware & resource monitoring
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import psutil

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger(__name__)

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/workspace")).resolve()


class SandboxTools:
    """Interface allowing the AI to operate its own containerized computer."""

    def __init__(self, workspace: Path = WORKSPACE_DIR) -> None:
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run_bash(self, cmd: str, timeout: int = 60) -> dict[str, Any]:
        """Execute any Linux shell command inside the AI's computer workspace."""
        try:
            logger.info("Executing bash command: %s", cmd)
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "exit_code": -1, "error": f"Command timed out after {timeout} seconds."}
        except Exception as exc:
            return {"success": False, "exit_code": -1, "error": str(exc)}

    def write_file(self, filename: str, content: str) -> dict[str, Any]:
        """Write code, documents, or data to the AI workspace."""
        try:
            target = (self.workspace / filename).resolve()
            # Ensure path stays inside workspace
            if not str(target).startswith(str(self.workspace)):
                return {"success": False, "error": "Access denied: Path outside workspace."}

            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            return {"success": True, "path": str(target), "bytes": len(content.encode("utf-8"))}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def read_file(self, filename: str, max_lines: int = 500) -> dict[str, Any]:
        """Read files from the AI workspace."""
        try:
            target = (self.workspace / filename).resolve()
            if not target.exists():
                return {"success": False, "error": f"File '{filename}' does not exist."}

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[:max_lines]

            return {"success": True, "content": "".join(lines), "total_lines": len(lines)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_files(self, subpath: str = "") -> dict[str, Any]:
        """List files and directories in the AI's workspace."""
        try:
            target = (self.workspace / subpath).resolve()
            if not target.exists():
                return {"success": False, "error": f"Path '{subpath}' does not exist."}

            items = []
            for entry in sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name.lower())):
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size_bytes": entry.stat().st_size if entry.is_file() else 0,
                })

            return {"success": True, "workspace": str(self.workspace), "items": items}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def fetch_web(self, url: str) -> dict[str, Any]:
        """Fetch and extract text content from any website."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VICY-Autonomous-Agent/2.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            if BeautifulSoup:
                soup = BeautifulSoup(html, "html.parser")
                for s in soup(["script", "style", "noscript"]):
                    s.decompose()
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                text = " ".join(soup.stripped_strings)
            else:
                title = "Web Page"
                text = re.sub(r"<[^>]+>", " ", html)
                text = " ".join(text.split())

            return {
                "success": True,
                "title": title,
                "text_snippet": text[:3000],
                "char_count": len(text),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_system_status(self) -> dict[str, Any]:
        """Get CPU, Memory, and Disk stats of the AI's virtual machine."""
        disk = psutil.disk_usage(str(self.workspace))
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_used_mb": round((mem.total - mem.available) / (1024 * 1024), 1),
            "ram_total_mb": round(mem.total / (1024 * 1024), 1),
            "ram_percent": mem.percent,
            "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
            "workspace_path": str(self.workspace),
        }
