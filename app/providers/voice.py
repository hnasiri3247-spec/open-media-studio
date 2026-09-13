import json
import uuid
from pathlib import Path

import httpx

from ..config import KOKORO_URL, MOCK_MODE, ASSETS_DIR


class VoiceProvider:
    async def health(self):
        if MOCK_MODE:
            return {"status": "mock"}

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                r = await client.get(f"{KOKORO_URL}/gradio_api/info")
                return {
                    "status": "online" if r.status_code < 400 else "offline"
                }
            except httpx.HTTPError:
                return {"status": "offline"}

    async def synthesize(
        self,
        text: str,
        voice: str = "af_sarah",
    ) -> Path:

        out = ASSETS_DIR / f"voice_{uuid.uuid4().hex}.wav"

        if MOCK_MODE:
            import wave

            with wave.open(str(out), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(b"\x00\x00" * 16000)

            return out

        payload = {
            "data": [
                text,
                voice,
                1.0,
            ]
        }

        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                f"{KOKORO_URL}/gradio_api/call/generate_speech",
                json=payload,
            )
            r.raise_for_status()

            event_id = r.json()["event_id"]

            async with client.stream(
                "GET",
                f"{KOKORO_URL}/gradio_api/call/generate_speech/{event_id}",
            ) as stream:

                stream.raise_for_status()

                async for line in stream.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()

                    if not raw or raw == "null":
                        continue

                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    urls = self._find_urls(data)

                    if urls:
                        audio_url = urls[0]

                        if audio_url.startswith("/"):
                            audio_url = f"{KOKORO_URL}{audio_url}"

                        audio = await client.get(audio_url)
                        audio.raise_for_status()

                        out.write_bytes(audio.content)
                        return out

        raise RuntimeError("Kokoro returned no audio file")

    def _find_urls(self, obj):
        urls = []

        if isinstance(obj, str):
            if obj.startswith(("http://", "https://")):
                urls.append(obj)

        elif isinstance(obj, dict):
            for value in obj.values():
                urls.extend(self._find_urls(value))

        elif isinstance(obj, list):
            for value in obj:
                urls.extend(self._find_urls(value))

        return urls
