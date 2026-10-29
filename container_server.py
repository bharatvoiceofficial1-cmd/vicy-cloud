"""
container_server.py — VICY 24/7 Cloud AI Core & Mission Control for Avi.

Features:
  - 24/7 Self-Keepalive loop (prevents Render free tier from sleeping)
  - Interactive Cyber Mission Control Web Dashboard on `/`
  - Interactive Phone Call Voice IVR on `/api/voice/ivr` (Avi can talk & assign tasks on call!)
  - Multi-Channel Notification Orchestration (Phone Call -> SMS -> Email)
  - Social Media & Website Manager Plugin APIs
  - Health check endpoint on `/healthz`
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from autonomous_agent import AutonomousAgent
from notifier import Notifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vicy_cloud")

app = FastAPI(title="VICY 24/7 Autonomous Cloud Core")
agent = AutonomousAgent()
notifier = Notifier()
active_sockets: list[WebSocket] = []
START_TIME = time.time()


class InstructionRequest(BaseModel):
    instruction: str


class OrchestrateRequest(BaseModel):
    task_name: str
    instruction: str


class ScheduleTaskRequest(BaseModel):
    name: str
    instruction: str
    interval_minutes: int = 60


class PluginDispatchRequest(BaseModel):
    action: str
    params: dict[str, Any] = {}


# ── 24/7 Self-Keepalive for Render ──────────────────────────────────────────

def _keepalive_loop():
    """Pings Render external URL every 10 minutes to stay awake 24/7."""
    time.sleep(15)  # Wait for startup
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        logger.info("RENDER_EXTERNAL_URL not set (local mode). Keepalive loop standing by.")
        return

    health_url = f"{url.rstrip('/')}/healthz"
    logger.info("24/7 Keepalive loop activated. Target: %s", health_url)
    while True:
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "VICY-KeepAlive/2.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                logger.debug("Keepalive ping successful: HTTP %d", resp.status)
        except Exception as exc:
            logger.warning("Keepalive ping notice: %s", exc)
        time.sleep(600)


threading.Thread(target=_keepalive_loop, daemon=True).start()


# ── Web UI Dashboard ────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Cyberpunk 24/7 Cloud Mission Control."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VICY // 24x7 Cloud Mission Control</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <style>
            :root {
                --neon-cyan: #00ffcc;
                --neon-pink: #ff007f;
                --neon-purple: #bc13fe;
                --bg-dark: #050811;
                --card-bg: rgba(10, 20, 35, 0.75);
                --border-glow: rgba(0, 255, 204, 0.3);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                background: radial-gradient(circle at 50% 20%, #0d1b2a 0%, var(--bg-dark) 80%);
                color: #e2e8f0;
                font-family: 'Rajdhani', sans-serif;
                min-height: 100vh;
                padding: 24px;
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid var(--neon-cyan);
                padding-bottom: 16px;
                margin-bottom: 24px;
            }
            h1 {
                font-family: 'Orbitron', sans-serif;
                font-size: 1.8rem;
                letter-spacing: 2px;
                color: var(--neon-cyan);
                text-shadow: 0 0 15px rgba(0, 255, 204, 0.6);
            }
            .status-pill {
                display: flex;
                align-items: center;
                gap: 8px;
                background: rgba(0, 255, 204, 0.1);
                border: 1px solid var(--neon-cyan);
                padding: 6px 14px;
                border-radius: 20px;
                font-family: 'Share Tech Mono', monospace;
                font-size: 0.9rem;
            }
            .dot {
                width: 10px; height: 10px; border-radius: 50%;
                background: var(--neon-cyan);
                box-shadow: 0 0 10px var(--neon-cyan);
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 24px;
            }
            @media(max-width: 768px) { .grid { grid-template-columns: 1fr; } }
            .card {
                background: var(--card-bg);
                border: 1px solid var(--border-glow);
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                backdrop-filter: blur(8px);
            }
            h3 {
                font-family: 'Orbitron', sans-serif;
                font-size: 1.1rem;
                color: var(--neon-pink);
                margin-bottom: 14px;
                letter-spacing: 1px;
            }
            .cmd-row { display: flex; gap: 10px; }
            input[type="text"] {
                flex: 1;
                background: rgba(5, 10, 20, 0.8);
                border: 1px solid var(--neon-cyan);
                color: #fff;
                padding: 12px 16px;
                border-radius: 6px;
                font-family: 'Share Tech Mono', monospace;
                font-size: 1rem;
                outline: none;
            }
            button {
                background: linear-gradient(135deg, var(--neon-pink), var(--neon-purple));
                color: #fff;
                border: none;
                padding: 12px 24px;
                font-family: 'Orbitron', sans-serif;
                font-weight: 700;
                border-radius: 6px;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 0 15px var(--neon-pink);
            }
            #terminal {
                height: 380px;
                background: #020408;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 14px;
                overflow-y: auto;
                font-family: 'Share Tech Mono', monospace;
                font-size: 0.9rem;
                line-height: 1.5;
            }
            .line-user { color: #38bdf8; }
            .line-agent { color: var(--neon-cyan); }
            .line-sys { color: #94a3b8; }
            .line-err { color: #f43f5e; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>VICY // 24x7 CLOUD AUTONOMOUS SANDBOX</h1>
            <div class="status-pill">
                <div class="dot"></div>
                <span id="liveStatus">CLOUD HOSTED: LIVE 24/7 (AVI'S MISSION CONTROL)</span>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>CLOUD ENVIRONMENT FOR AVI</h3>
                <p><strong>Owner:</strong> Avi (+918840795166)</p>
                <p><strong>Escalation Channel:</strong> Voice Call &rarr; SMS &rarr; Email (PC Off Mode)</p>
                <p><strong>Execution Core:</strong> Isolated Linux Container (/workspace)</p>
                <p><strong>Plugins Active:</strong> YouTube SEO, Instagram, FB Pages, WhatsApp, LinkedIn, WordPress</p>
            </div>
            <div class="card">
                <h3>DISPATCH INSTRUCTION</h3>
                <div class="cmd-row">
                    <input type="text" id="cmdInput" placeholder="e.g. 'write a python scraper', 'check website status https://google.com', 'schedule news summary every 60 min'">
                    <button onclick="sendCmd()">DISPATCH</button>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>REAL-TIME MISSION TERMINAL FEED</h3>
            <div id="terminal"></div>
        </div>

        <script>
            const term = document.getElementById('terminal');
            function appendLog(text, cls='line-agent') {
                const row = document.createElement('div');
                row.className = cls;
                const time = new Date().toLocaleTimeString();
                row.innerText = `[${time}] ${text}`;
                term.appendChild(row);
                term.scrollTop = term.scrollHeight;
            }

            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = () => appendLog("Neural uplink connected. Welcome back, Avi.", "line-sys");
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.reply) appendLog(data.reply, "line-agent");
                else if (data.result) appendLog(JSON.stringify(data.result, null, 2), "line-agent");
                else appendLog(JSON.stringify(data, null, 2), "line-sys");
            };
            ws.onerror = (e) => appendLog("Uplink error", "line-err");

            function sendCmd() {
                const inp = document.getElementById('cmdInput');
                const val = inp.value.trim();
                if (!val) return;
                appendLog(`> AVI: ${val}`, "line-user");
                ws.send(JSON.stringify({ instruction: val }));
                inp.value = '';
            }

            document.getElementById('cmdInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendCmd();
            });
        </script>
    </body>
    </html>
    """


# ── Interactive Phone Call Voice IVR (Avi can talk on the phone!) ────────────

@app.post("/api/voice/ivr")
async def voice_ivr_webhook(request: Request) -> Response:
    """
    Twilio Voice Webhook:
    When Avi speaks over the phone, Twilio sends SpeechResult.
    VICY executes the spoken command and speaks back!
    """
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")

    if speech_result:
        logger.info("Avi spoke command over phone: %s", speech_result)
        res = agent.execute_instruction(str(speech_result))
        summary = str(res.get("reply") or res.get("result") or "Action complete")[:250].replace("<", "").replace(">", "")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi">Avi, I executed your request: {summary}.</Say>
    <Gather input="speech" timeout="5" action="/api/voice/ivr">
        <Say>You can give me another command now, or hang up.</Say>
    </Gather>
</Response>"""
    else:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi">Hello Avi, this is VICY. Your autonomous cloud assistant is listening.</Say>
    <Gather input="speech" timeout="6" action="/api/voice/ivr">
        <Say>Please speak your command after the tone.</Say>
    </Gather>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


# ── Health Check, Execution & Plugins ───────────────────────────────────────

@app.get("/healthz")
async def health_check() -> dict[str, Any]:
    uptime_sec = int(time.time() - START_TIME)
    return {
        "status": "healthy",
        "service": "VICY 24/7 Cloud Core",
        "owner": "Avi",
        "uptime_seconds": uptime_sec,
        "tasks_running": len(agent.task_daemon.list_tasks()),
    }


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    return {
        "status": "online",
        "owner": "Avi",
        "phone": "+918840795166",
        "system": agent.tools.get_system_status(),
        "tasks": agent.task_daemon.list_tasks(),
    }


@app.post("/api/instruct")
async def instruct(req: InstructionRequest) -> dict[str, Any]:
    return agent.execute_instruction(req.instruction)


@app.post("/api/orchestrate")
async def orchestrate_task(req: OrchestrateRequest) -> dict[str, Any]:
    """Execute task on cloud and escalate notifications to Avi."""
    result = agent.execute_instruction(req.instruction)
    summary = str(result.get("reply") or result.get("result") or result)[:400]
    
    # Notify Avi via Call -> SMS -> Email
    notify_res = notifier.notify_task_complete(
        task_name=req.task_name,
        result_summary=summary,
        pc_is_online=False
    )
    return {
        "task_name": req.task_name,
        "result": result,
        "notifications": notify_res,
    }


@app.post("/api/plugins/dispatch")
async def dispatch_plugin(req: PluginDispatchRequest) -> dict[str, Any]:
    """Dispatch action to YouTube, Meta, WhatsApp, LinkedIn, or Website plugins."""
    return agent.plugins.dispatch(req.action, req.params)


@app.post("/api/tasks/schedule")
async def schedule_task(req: ScheduleTaskRequest) -> dict[str, Any]:
    info = agent.task_daemon.add_scheduled_task(req.name, req.instruction, req.interval_minutes)
    return {"status": "scheduled", "task": info}


@app.get("/api/files")
async def list_files(subpath: str = "") -> dict[str, Any]:
    return agent.tools.list_files(subpath)


@app.websocket("/ws")
async def websocket_terminal(websocket: WebSocket) -> None:
    await websocket.accept()
    active_sockets.append(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "info", "message": "24/7 Cloud Core Online for Avi."}))
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                inst = data.get("instruction", "")
                if inst:
                    res = agent.execute_instruction(inst)
                    await websocket.send_text(json.dumps(res))
            except Exception as e:
                await websocket.send_text(json.dumps({"error": str(e)}))
    except WebSocketDisconnect:
        if websocket in active_sockets:
            active_sockets.remove(websocket)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info("Starting VICY Cloud Server for Avi on port %d...", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
