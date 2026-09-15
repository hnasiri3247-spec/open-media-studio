import asyncio
import json
import uuid
from pathlib import Path

import httpx
from gradio_client import Client

from ..config import WAN_URL, MOCK_MODE, ASSETS_DIR


class ComfyUIProvider:
    def __init__(self, base_url=WAN_URL):
        self.base_url = base_url.rstrip("/")
        self._jobs = {}

    async def health(self):
        if MOCK_MODE:
            return {"status": "online"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{self.base_url}/gradio_api/info")
                return {
                    "status": "online" if r.status_code < 400 else "offline"
                }
        except httpx.HTTPError:
            return {"status": "offline"}

    async def submit(self, scene_prompt: str, duration: int):
        if MOCK_MODE:
            prompt_id = "mock-" + uuid.uuid4().hex
            self._jobs[prompt_id] = {"mock": True}
            return {"prompt_id": prompt_id}

        prompt_id = uuid.uuid4().hex
        frames = max(25, min(int(duration) * 15, 145))

        def run_job():
            client = Client(self.base_url)
            job = client.submit(
                scene_prompt,
                None,
                832,
                512,
                frames,
                20,
                5.0,
                -1,
                api_name="/generate_video",
            )
            return job.result(timeout=900)

        self._jobs[prompt_id] = await asyncio.to_thread(run_job)
        return {"prompt_id": prompt_id}

    async def wait_for_output(
        self,
        prompt_id: str,
        timeout: int = 900,
        poll: float = 2.0,
    ):
        if MOCK_MODE:
            return self._jobs.get(prompt_id, {"mock": True})

        if prompt_id not in self._jobs:
            raise RuntimeError(f"Wan job not found: {prompt_id}")

        return self._jobs[prompt_id]

    def _find_urls(self, obj):
        found = []

        if isinstance(obj, str):
            if obj.startswith(("http://", "https://")):
                found.append(obj)

        elif isinstance(obj, dict):
            for value in obj.values():
                found.extend(self._find_urls(value))

        elif isinstance(obj, list):
            for value in obj:
                found.extend(self._find_urls(value))

        return found

    async def download_outputs(self, history_item):
        if MOCK_MODE:
            return []

        urls = self._find_urls(history_item)

        if not urls:
            raise RuntimeError(
                f"Wan returned no downloadable video URL: {history_item}"
            )

        video_url = next(
            (
                u for u in urls
                if ".mp4" in u.lower()
                or "file=" in u.lower()
            ),
            urls[0],
        )

        out = ASSETS_DIR / f"scene_{uuid.uuid4().hex}.mp4"

        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.get(video_url)
            r.raise_for_status()
            out.write_bytes(r.content)

        return [out]
