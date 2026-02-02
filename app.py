"""Kai's Personal Dashboard - Private status & achievements tracker."""

import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

app = FastAPI(title="Kai Dashboard")
security = HTTPBasic()

# Config
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "kai")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "ablent2026")
DATA_FILE = Path(__file__).parent / "data.json"
WORKSPACE = Path.home() / ".openclaw" / "workspace"


def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify dashboard credentials."""
    if not secrets.compare_digest(credentials.username, DASHBOARD_USER):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    if not secrets.compare_digest(credentials.password, DASHBOARD_PASS):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return True


def load_data() -> dict:
    """Load dashboard data."""
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {
        "token_usage": {"total": 0, "today": 0, "week": 0},
        "achievements_24h": [],
        "achievements_week": [],
        "todo": [],
        "last_updated": None,
    }


def save_data(data: dict):
    """Save dashboard data."""
    data["last_updated"] = datetime.now().isoformat()
    DATA_FILE.write_text(json.dumps(data, indent=2))


def get_token_usage() -> dict:
    """Get token usage from OpenClaw stats."""
    # Try to read from OpenClaw session stats
    stats_file = WORKSPACE / ".openclaw" / "stats.json"
    if stats_file.exists():
        try:
            stats = json.loads(stats_file.read_text())
            return {
                "total": stats.get("total_tokens", 0),
                "today": stats.get("today_tokens", 0),
                "week": stats.get("week_tokens", 0),
            }
        except:
            pass
    
    # Fallback to stored data
    data = load_data()
    return data.get("token_usage", {"total": 0, "today": 0, "week": 0})


def get_achievements() -> tuple:
    """Get achievements from memory files."""
    achievements_24h = []
    achievements_week = []
    
    memory_dir = WORKSPACE / "memory"
    now = datetime.now()
    
    if memory_dir.exists():
        for f in sorted(memory_dir.glob("*.md"), reverse=True):
            try:
                date_str = f.stem  # e.g., "2026-02-02"
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                content = f.read_text()
                
                # Extract achievements (lines starting with - [x] or ✓)
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("- [x]") or line.startswith("✓") or "completed" in line.lower():
                        achievement = line.lstrip("- [x]✓ ").strip()
                        if achievement:
                            if (now - file_date).days < 1:
                                achievements_24h.append(achievement)
                            if (now - file_date).days < 7:
                                achievements_week.append(achievement)
            except:
                continue
    
    # Also check stored achievements
    data = load_data()
    achievements_24h.extend(data.get("achievements_24h", []))
    achievements_week.extend(data.get("achievements_week", []))
    
    return list(set(achievements_24h))[:20], list(set(achievements_week))[:50]


def get_todos() -> list:
    """Get todo items from HEARTBEAT.md and stored data."""
    todos = []
    
    # Check HEARTBEAT.md
    heartbeat = WORKSPACE / "HEARTBEAT.md"
    if heartbeat.exists():
        content = heartbeat.read_text()
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- [ ]"):
                todos.append({"task": line[5:].strip(), "done": False, "source": "heartbeat"})
            elif line.startswith("- [x]"):
                todos.append({"task": line[5:].strip(), "done": True, "source": "heartbeat"})
    
    # Add stored todos
    data = load_data()
    for todo in data.get("todo", []):
        if todo not in todos:
            todos.append(todo)
    
    return todos[:30]


@app.get("/", response_class=HTMLResponse)
async def dashboard(auth: bool = Depends(verify_auth)):
    """Render the dashboard."""
    token_usage = get_token_usage()
    achievements_24h, achievements_week = get_achievements()
    todos = get_todos()
    
    # Build HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kai Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; }}
        .card {{ background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }}
        .glow {{ box-shadow: 0 0 20px rgba(59,130,246,0.3); }}
    </style>
</head>
<body class="text-white p-4 md:p-8">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <header class="flex items-center justify-between mb-8">
            <div class="flex items-center gap-4">
                <div class="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl font-bold glow">⚡</div>
                <div>
                    <h1 class="text-3xl font-bold">Kai</h1>
                    <p class="text-gray-400">AI Operative @ ablent.ai</p>
                </div>
            </div>
            <div class="text-right text-sm text-gray-400">
                <div>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
                <div>Status: <span class="text-green-400">● Online</span></div>
            </div>
        </header>

        <!-- Contact Details -->
        <div class="card rounded-xl p-6 mb-6">
            <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">📇 Contact Details</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-gray-800/50 rounded-lg p-4">
                    <div class="text-gray-400 text-sm">Email</div>
                    <div class="font-mono">kai.ablent@proton.me</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-4">
                    <div class="text-gray-400 text-sm">GitHub</div>
                    <div class="font-mono">crosseyedlion</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-4">
                    <div class="text-gray-400 text-sm">Employer</div>
                    <div class="font-mono">ablent.ai</div>
                </div>
            </div>
        </div>

        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-blue-400">{token_usage.get('total', 0):,}</div>
                <div class="text-gray-400 mt-2">Total Tokens</div>
            </div>
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-green-400">{token_usage.get('today', 0):,}</div>
                <div class="text-gray-400 mt-2">Tokens Today</div>
            </div>
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-purple-400">{token_usage.get('week', 0):,}</div>
                <div class="text-gray-400 mt-2">Tokens This Week</div>
            </div>
        </div>

        <!-- Achievements -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <!-- 24h Achievements -->
            <div class="card rounded-xl p-6">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">🏆 Last 24 Hours</h2>
                <ul class="space-y-2">
                    {"".join(f'<li class="flex items-start gap-2"><span class="text-green-400">✓</span><span>{a}</span></li>' for a in achievements_24h[:10]) or '<li class="text-gray-500">No achievements yet today</li>'}
                </ul>
            </div>

            <!-- Week Achievements -->
            <div class="card rounded-xl p-6">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">📅 This Week</h2>
                <ul class="space-y-2">
                    {"".join(f'<li class="flex items-start gap-2"><span class="text-blue-400">✓</span><span>{a}</span></li>' for a in achievements_week[:10]) or '<li class="text-gray-500">No achievements this week</li>'}
                </ul>
            </div>
        </div>

        <!-- Todo List -->
        <div class="card rounded-xl p-6">
            <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">📋 To-Do List</h2>
            <ul class="space-y-2">
                {"".join(f'''<li class="flex items-center gap-3 p-2 rounded {'bg-green-900/20' if t.get('done') else 'bg-gray-800/30'}">
                    <span class="{'text-green-400' if t.get('done') else 'text-gray-500'}">{'☑' if t.get('done') else '☐'}</span>
                    <span class="{'line-through text-gray-500' if t.get('done') else ''}">{t.get('task', '')}</span>
                </li>''' for t in todos[:15]) or '<li class="text-gray-500 p-2">No tasks</li>'}
            </ul>
        </div>

        <!-- Footer -->
        <footer class="mt-8 text-center text-gray-500 text-sm">
            <p>Kai Dashboard v1.0 | Built with ⚡ by Kai</p>
        </footer>
    </div>

    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => location.reload(), 300000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


# API endpoints for updating data
class Achievement(BaseModel):
    text: str
    period: str = "24h"  # "24h" or "week"


class Todo(BaseModel):
    task: str
    done: bool = False


@app.post("/api/achievement")
async def add_achievement(achievement: Achievement, auth: bool = Depends(verify_auth)):
    """Add an achievement."""
    data = load_data()
    if achievement.period == "24h":
        data["achievements_24h"].append(achievement.text)
    else:
        data["achievements_week"].append(achievement.text)
    save_data(data)
    return {"status": "ok"}


@app.post("/api/todo")
async def add_todo(todo: Todo, auth: bool = Depends(verify_auth)):
    """Add a todo item."""
    data = load_data()
    data["todo"].append({"task": todo.task, "done": todo.done})
    save_data(data)
    return {"status": "ok"}


@app.post("/api/tokens")
async def update_tokens(total: int = 0, today: int = 0, week: int = 0, auth: bool = Depends(verify_auth)):
    """Update token usage."""
    data = load_data()
    data["token_usage"] = {"total": total, "today": today, "week": week}
    save_data(data)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
