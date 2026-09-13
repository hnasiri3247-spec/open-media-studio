# Open Media Studio MVP

Local-first media generation pipeline:

- FastAPI orchestration API
- ComfyUI/Wan adapter for video/image jobs
- Kokoro adapter for TTS
- AudioCraft adapter for music/SFX
- FFmpeg final render
- Android WebView client shell

## Run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/ui/`.

Set values in `.env` (copy `.env.example`) when real local providers are available. Keep `MOCK_MODE=true` for pipeline testing.

## ComfyUI

Export an API-format workflow JSON from ComfyUI into `workflows/` and set `COMFYUI_WORKFLOW` to that file. The adapter replaces `{{PROMPT}}` and `{{DURATION}}` in the JSON before submission.

## Tests

```bash
pytest -q
```
