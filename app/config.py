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

WAN_URL = os.getenv(
    "WAN_URL",
    "https://alexcheng0072-free-video-generator.hf.space"
).rstrip("/")

KOKORO_URL = os.getenv(
    "KOKORO_URL",
    "https://kinabraytan-kokoro-tts-server.hf.space"
).rstrip("/")

MUSICGEN_URL = os.getenv(
    "MUSICGEN_URL",
    "https://sanchit-gandhi-musicgen-streaming.hf.space"
).rstrip("/")

AUDIOGEN_URL = os.getenv(
    "AUDIOGEN_URL",
    "https://fffiloni-audiogen.hf.space"
).rstrip("/")

FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
