import json
import time
import uuid
from pathlib import Path
import httpx
from ..config import COMFYUI_URL, COMFYUI_WORKFLOW, MOCK_MODE, ASSETS_DIR

class ComfyUIProvider:
    def __init__(self, base_url=COMFYUI_URL):
        self.base_url = base_url.rstrip('/')

    async def health(self):
        if MOCK_MODE:
            return {"status": "mock"}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{self.base_url}/system_stats")
            r.raise_for_status()
            return {"status": "online", "details": r.json()}

    def _workflow(self, scene_prompt: str, duration: int):
        if not COMFYUI_WORKFLOW:
            # Minimal generic workflow contract. A real Wan workflow can be supplied via COMFYUI_WORKFLOW.
            return {"scene_prompt": scene_prompt, "duration": duration}
        data = json.loads(Path(COMFYUI_WORKFLOW).read_text(encoding='utf-8'))
        raw = json.dumps(data)
        raw = raw.replace("{{PROMPT}}", scene_prompt).replace("{{DURATION}}", str(duration))
        return json.loads(raw)

    async def submit(self, scene_prompt: str, duration: int):
        if MOCK_MODE:
            return {"prompt_id": "mock-" + uuid.uuid4().hex}
        workflow = self._workflow(scene_prompt, duration)
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{self.base_url}/prompt", json={"prompt": workflow, "client_id": str(uuid.uuid4())})
            r.raise_for_status()
            return r.json()

    async def history(self, prompt_id: str):
        if MOCK_MODE:
            return {prompt_id: {"status": {"completed": True}, "outputs": {}}}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}/history/{prompt_id}")
            r.raise_for_status()
            return r.json()

    async def wait_for_output(self, prompt_id: str, timeout: int = 900, poll: float = 2.0):
        if MOCK_MODE:
            return None
        started = time.time()
        while time.time() - started < timeout:
            data = await self.history(prompt_id)
            item = data.get(prompt_id)
            if item and item.get("outputs"):
                return item
            await __import__('asyncio').sleep(poll)
        raise TimeoutError(f"ComfyUI job timed out: {prompt_id}")

    async def download_outputs(self, history_item: dict):
        saved = []
        if MOCK_MODE:
            return saved
        outputs = history_item.get("outputs", {})
        async with httpx.AsyncClient(timeout=120) as client:
            for node_output in outputs.values():
                for key in ("gifs", "videos", "images"):
                    for item in node_output.get(key, []) or []:
                        filename = item.get("filename")
                        if not filename:
                            continue
                        params = {k: item[k] for k in ("filename", "subfolder", "type") if k in item}
                        r = await client.get(f"{self.base_url}/view", params=params)
                        r.raise_for_status()
                        ext = Path(filename).suffix or (".mp4" if key in ("gifs", "videos") else ".png")
                        out = ASSETS_DIR / f"scene_{uuid.uuid4().hex}{ext}"
                        out.write_bytes(r.content)
                        saved.append(out)
        return saved
