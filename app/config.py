import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "storage"))
PROJECTS_DIR = DATA_DIR / "projects"
ASSETS_DIR = DATA_DIR / "assets"
RENDERS_DIR = DATA_DIR / "renders"
for p in (PROJECTS_DIR, ASSETS_DIR, RENDERS_DIR):
    p.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_WORKFLOW = os.getenv("COMFYUI_WORKFLOW", "").strip()
KOKORO_URL = os.getenv("KOKORO_URL", "http://127.0.0.1:8880").rstrip("/")
AUDIOCRAFT_URL = os.getenv("AUDIOCRAFT_URL", "http://127.0.0.1:8881").rstrip("/")
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
