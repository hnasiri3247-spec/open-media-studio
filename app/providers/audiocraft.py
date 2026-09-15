import json
import subprocess
import uuid
from pathlib import Path

import httpx

from ..config import (
    MUSICGEN_URL,
    AUDIOGEN_URL,
    FFMPEG_BIN,
    MOCK_MODE,
    ASSETS_DIR,
)


class AudioCraftProvider:
    async def health(self):
        if MOCK_MODE:
            return {"status": "mock"}

        results = {}

        async with httpx.AsyncClient(timeout=20) as client:
            for name, url in (
                ("musicgen", MUSICGEN_URL),
                ("audiogen", AUDIOGEN_URL),
            ):
                try:
                    r = await client.get(f"{url}/gradio_api/info")
                    results[name] = (
                        "online" if r.status_code < 400 else "offline"
                    )
                except httpx.HTTPError:
                    results[name] = "offline"

        return {
            "status": (
                "online"
                if all(v == "online" for v in results.values())
                else "offline"
            ),
            "details": results,
        }

    async def generate_music(self, prompt: str, duration: int) -> Path:
        return await self._musicgen(prompt, duration)

    async def generate_sfx(self, prompt: str, duration: int) -> Path:
        return await self._audiogen(prompt, duration)

    async def _musicgen(self, prompt: str, duration: int) -> Path:
        out = ASSETS_DIR / f"music_{uuid.uuid4().hex}.wav"

        if MOCK_MODE:
            return self._mock_wav(out, duration)

        duration = max(10, min(int(duration), 30))

        payload = {
            "data": [
                prompt,
                duration,
                1.5,
                5,
            ]
        }

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{MUSICGEN_URL}/gradio_api/call/generate_audio",
                json=payload,
            )
            r.raise_for_status()
            event = r.json()["event_id"]

            async with client.stream(
                "GET",
                f"{MUSICGEN_URL}/gradio_api/call/generate_audio/{event}",
            ) as stream:
                stream.raise_for_status()

                async for line in stream.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if not raw:
                        continue

                    data = json.loads(raw)
                    urls = self._find_urls(data)

                    if urls:
                        playlist = next(
                            (
                                u for u in urls
                                if "playlist.m3u8" in u
                            ),
                            urls[0],
                        )

                        self._ffmpeg_audio(playlist, out)
                        return out

        raise RuntimeError("MusicGen returned no audio")

    async def _audiogen(self, prompt: str, duration: int) -> Path:
        out = ASSETS_DIR / f"sfx_{uuid.uuid4().hex}.wav"

        if MOCK_MODE:
            return self._mock_wav(out, duration)

        payload = {
            "data": [
                prompt,
                float(duration),
            ]
        }

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{AUDIOGEN_URL}/gradio_api/call/infer",
                json=payload,
            )
            r.raise_for_status()
            event = r.json()["event_id"]

            async with client.stream(
                "GET",
                f"{AUDIOGEN_URL}/gradio_api/call/infer/{event}",
            ) as stream:
                stream.raise_for_status()

                async for line in stream.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if not raw:
                        continue

                    data = json.loads(raw)
                    urls = self._find_urls(data)

                    if urls:
                        audio = await client.get(urls[0])
                        audio.raise_for_status()
                        out.write_bytes(audio.content)
                        return out

        raise RuntimeError("AudioGen returned no audio")

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

    def _ffmpeg_audio(self, source, output):
        subprocess.run(
            [
                FFMPEG_BIN,
                "-y",
                "-i",
                source,
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _mock_wav(self, out, duration):
        import wave

        frames = 16000 * max(1, int(duration))

        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * frames)

        return out
