import uuid
import httpx
from pathlib import Path
from ..config import KOKORO_URL, MOCK_MODE, ASSETS_DIR

class VoiceProvider:
    async def health(self):
        if MOCK_MODE:
            return {"status": "mock"}
        async with httpx.AsyncClient(timeout=10) as client:
            for endpoint in ("/healthz", "/health", "/tts/status"):
                try:
                    r = await client.get(f"{KOKORO_URL}{endpoint}")
                    if r.status_code < 500:
                        return {"status": "online", "endpoint": endpoint, "details": r.json() if r.content else {}}
                except httpx.HTTPError:
                    pass
        return {"status": "offline"}

    async def synthesize(self, text: str, voice: str = "af_heart") -> Path:
        out = ASSETS_DIR / f"voice_{uuid.uuid4().hex}.wav"
        if MOCK_MODE:
            import wave
            with wave.open(str(out), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                w.writeframes(b"\x00\x00" * 16000)
            return out
        payload = {"text": text, "voice": voice}
        endpoints = ("/tts/generate", "/tts", "/v1/audio/speech")
        async with httpx.AsyncClient(timeout=300) as client:
            last = None
            for endpoint in endpoints:
                try:
                    if endpoint == "/v1/audio/speech":
                        r = await client.post(f"{KOKORO_URL}{endpoint}", json={"input": text, "voice": voice, "response_format": "wav"})
                    else:
                        r = await client.post(f"{KOKORO_URL}{endpoint}", json=payload)
                    if r.status_code < 400:
                        out.write_bytes(r.content)
                        return out
                    last = r
                except httpx.HTTPError as e:
                    last = e
            raise RuntimeError(f"Kokoro TTS request failed: {last}")
