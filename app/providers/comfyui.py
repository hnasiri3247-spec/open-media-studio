import asyncio
import json
import uuid
from pathlib import Path

import httpx

from ..config import WAN_URL, MOCK_MODE, ASSETS_DIR


class ComfyUIProvider:
    """
    Kept under the existing class name so main.py does not need
    structural changes. It now talks to the validated Wan Gradio Space.
    """

    def __init__(self, base_url=WAN_URL):
        self.base_url = base_url.rstrip("/")

    async def health(self):
        if MOCK_MODE:
            return {"status": "mock"}

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                r = await client.get(f"{self.base_url}/gradio_api/info")
                return {
                    "status": "online" if r.status_code < 400 else "offline"
                }
            except httpx.HTTPError:
                return {"status": "offline"}

    async def submit(self, scene_prompt: str, duration: int):
        if MOCK_MODE:
            return {"prompt_id": "mock-" + uuid.uuid4().hex}

        payload = {
            "data": [
                None,
                scene_prompt,
                "832x480",
                max(2, min(int(duration), 5)),
            ]
        }

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.base_url}/gradio_api/call/generate_video",
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    async def wait_for_output(
        self,
        prompt_id: str,
        timeout: int = 900,
        poll: float = 2.0,
    ):
        if MOCK_MODE:
            return {"mock": True}

        started = asyncio.get_event_loop().time()

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "GET",
                f"{self.base_url}/gradio_api/call/generate_video/{prompt_id}",
            ) as r:
                r.raise_for_status()

                async for line in r.aiter_lines():
                    if asyncio.get_event_loop().time() - started > timeout:
                        raise TimeoutError(
                            f"Wan job timed out: {prompt_id}"
                        )

                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if not raw:
                        continue

                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if isinstance(data, list) and data:
                        return data

                    if isinstance(data, dict):
                        return data

        raise TimeoutError(f"Wan job ended without output: {prompt_id}")

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
            raise RuntimeError("Wan returned no downloadable video URL")

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
