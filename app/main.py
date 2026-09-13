from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .models import ProjectCreate, SceneCreate, VoiceCreate, MediaRequest, RenderRequest
from .store import create_project, get_project, save_project
from .providers.comfyui import ComfyUIProvider
from .providers.voice import VoiceProvider
from .providers.audiocraft import AudioCraftProvider
from .services.render import render_video

app = FastAPI(title="Open Media Studio MVP", version="0.2.0")
comfy = ComfyUIProvider()
voice = VoiceProvider()
audio = AudioCraftProvider()
ROOT = Path(__file__).resolve().parents[1]
app.mount("/ui", StaticFiles(directory=ROOT / "frontend", html=True), name="ui")

@app.get("/")
def root():
    return {"name": "Open Media Studio MVP", "ui": "/ui/", "status": "ok", "version": app.version}

@app.get("/api/health")
async def health():
    services = {"app": "ok"}
    for name, provider in (("comfyui", comfy), ("kokoro", voice), ("audiocraft", audio)):
        try:
            services[name] = (await provider.health())["status"]
        except Exception:
            services[name] = "offline"
    import shutil
    services["ffmpeg"] = "available" if shutil.which("ffmpeg") else "offline"
    return {"status": "ok", "services": services}

@app.post("/api/projects")
def new_project(data: ProjectCreate):
    return create_project(data)

@app.get("/api/projects/{pid}")
def read_project(pid: str):
    p = get_project(pid)
    if not p: raise HTTPException(404, "project not found")
    return p

@app.post("/api/projects/{pid}/scenes")
async def add_scene(pid: str, data: SceneCreate):
    p = get_project(pid)
    if not p: raise HTTPException(404, "project not found")
    job = await comfy.submit(data.prompt, data.duration)
    scene = {"id": len(p["scenes"]) + 1, "prompt": data.prompt, "duration": data.duration, "job": job, "media": []}
    if not str(job.get("prompt_id", "")).startswith("mock-"):
        history = await comfy.wait_for_output(job["prompt_id"])
        files = await comfy.download_outputs(history)
        scene["media"] = [str(x) for x in files]
    p["scenes"].append(scene)
    p["status"] = "scenes_ready"
    return save_project(p)

@app.post("/api/projects/{pid}/voice")
async def add_voice(pid: str, data: VoiceCreate):
    p = get_project(pid)
    if not p: raise HTTPException(404, "project not found")
    path = await voice.synthesize(data.text, data.voice)
    p["audio"].append({"type": "voice", "voice": data.voice, "text": data.text, "path": str(path)})
    return save_project(p)

@app.post("/api/projects/{pid}/music")
async def add_music(pid: str, data: MediaRequest):
    p = get_project(pid)
    if not p: raise HTTPException(404, "project not found")
    path = await audio.generate_music(data.prompt, data.duration)
    p["audio"].append({"type": "music", "prompt": data.prompt, "path": str(path)})
    return save_project(p)

@app.post("/api/projects/{pid}/sfx")
async def add_sfx(pid: str, data: MediaRequest):
    p = get_project(pid)
    if not p: raise HTTPException(404, "project not found")
    path = await audio.generate_sfx(data.prompt, data.duration)
    p["audio"].append({"type": "sfx", "prompt": data.prompt, "path": str(path)})
    return save_project(p)

@app.post("/api/projects/{pid}/render")
def render(pid: str, data: RenderRequest):
    p = get_project(pid)
    if not p: raise HTTPException(404, "project not found")
    if data.project_id != pid: raise HTTPException(400, "project_id mismatch")
    media = [Path(m) for s in p.get("scenes", []) for m in s.get("media", [])]
    audio_paths = [Path(x["path"]) for x in p.get("audio", []) if x.get("path")]
    out = render_video(pid, p["duration"], p["format"], media=media, audio=audio_paths)
    p["render"] = str(out)
    p["status"] = "rendered"
    save_project(p)
    return {"status": "rendered", "file": f"/api/projects/{pid}/render/download"}

@app.get("/api/projects/{pid}/render/download")
def download_render(pid: str):
    p = get_project(pid)
    if not p or not p.get("render"): raise HTTPException(404, "render not found")
    return FileResponse(p["render"], media_type="video/mp4", filename=f"{pid}.mp4")
