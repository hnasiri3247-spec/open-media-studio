import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .config import PROJECTS_DIR


def now():
    return datetime.now(timezone.utc).isoformat()


def create_project(data):
    pid = uuid4().hex
    project = {
        "id": pid,
        "created_at": now(),
        "updated_at": now(),
        "status": "draft",
        "title": data.title,
        "script": data.script,
        "format": data.format,
        "duration": data.duration,
        "style": data.style,
        "scenes": [],
        "assets": [],
        "audio": [],
        "render": None,
    }
    save_project(project)
    return project


def project_path(pid):
    return PROJECTS_DIR / f"{pid}.json"


def save_project(project):
    project["updated_at"] = now()
    project_path(project["id"]).write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def get_project(pid):
    p = project_path(pid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
