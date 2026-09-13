import uuid
from pathlib import Path
import httpx
from ..config import AUDIOCRAFT_URL, MOCK_MODE, ASSETS_DIR

class AudioCraftProvider:
    async def health(self):
        if MOCK_MODE:
            return {"status": "mock"}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{AUDIOCRAFT_URL}/health")
            r.raise_for_status()
            return {"status": "online", "details": r.json() if r.content else {}}

    async def generate_music(self, prompt: str, duration: int) -> Path:
        return await self._generate("music", prompt, duration)

    async def generate_sfx(self, prompt: str, duration: int) -> Path:
        return await self._generate("sfx", prompt, duration)

    async def _generate(self, kind, prompt, duration):
        out = ASSETS_DIR / f"{kind}_{uuid.uuid4().hex}.wav"
        if MOCK_MODE:
            import wave
            frames = 16000 * duration
            with wave.open(str(out), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                w.writeframes(b"\x00\x00" * frames)
            return out
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{AUDIOCRAFT_URL}/generate", json={"type": kind, "prompt": prompt, "duration": duration})
            r.raise_for_status()
            out.write_bytes(r.content)
        return out
