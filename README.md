# VICY 24/7 Cloud Autonomous AI Sandbox

An autonomous AI agent running on its own dedicated cloud environment with 24/7 uptime on Render.

## Features
- **24/7 Always-On Execution**: Autonomous background scheduler (`task_daemon.py`) and keepalive ping loop.
- **Dedicated Cloud Sandbox**: Full Linux shell (`bash`), Python runtime, web scraper, and file workspace.
- **Cyberpunk Web Interface**: Real-time terminal streaming over WebSocket on `/`.
- **Health Check & Keepalive**: Built-in `/healthz` endpoint.
- **Dual-Brain Architecture**: Powered by Gemini 3 Flash Preview with persistent memory.

## Deploying to Render
1. Push this repository to GitHub.
2. In Render Dashboard ([dashboard.render.com](https://dashboard.render.com)):
   - Click **New +** -> **Blueprint** (or **Web Service**).
   - Select your GitHub repository.
   - Render automatically reads `render.yaml` and deploys your Docker container.
3. Access your live AI at your Render URL: `https://<your-service-name>.onrender.com`.
