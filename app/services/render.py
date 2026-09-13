import subprocess
from pathlib import Path
from ..config import FFMPEG_BIN, RENDERS_DIR


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def render_video(project_id: str, duration: int, ratio: str, media: list[Path] | None = None, audio: list[Path] | None = None) -> Path:
    out = RENDERS_DIR / f"{project_id}.mp4"
    size = {"9:16": "1080x1920", "16:9": "1920x1080", "1:1": "1080x1080"}[ratio]
    media = [p for p in (media or []) if p.exists()]
    audio = [p for p in (audio or []) if p.exists()]

    visual = RENDERS_DIR / f"{project_id}_visual.mp4"
    if media:
        normalized = []
        per_clip = max(1, duration // len(media))
        for i, p in enumerate(media):
            n = RENDERS_DIR / f"{project_id}_part_{i}.mp4"
            vf = f"scale={size}:force_original_aspect_ratio=decrease,pad={size}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            if p.suffix.lower() in {'.mp4', '.webm', '.mov', '.mkv'}:
                cmd = [FFMPEG_BIN, '-y', '-i', str(p), '-t', str(per_clip), '-vf', vf, '-r', '30', '-c:v', 'libx264', '-an', str(n)]
            else:
                cmd = [FFMPEG_BIN, '-y', '-loop', '1', '-i', str(p), '-t', str(per_clip), '-vf', vf, '-r', '30', '-c:v', 'libx264', '-an', str(n)]
            _run(cmd)
            normalized.append(n)
        concat = RENDERS_DIR / f"{project_id}_concat.txt"
        concat.write_text(''.join(f"file '{p.as_posix()}'\n" for p in normalized), encoding='utf-8')
        _run([FFMPEG_BIN, '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-t', str(duration), '-c', 'copy', str(visual)])
    else:
        _run([FFMPEG_BIN, '-y', '-f', 'lavfi', '-i', f"color=c=black:s={size}:r=30", '-t', str(duration), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(visual)])

    cmd = [FFMPEG_BIN, '-y', '-i', str(visual)]
    if audio:
        for p in audio:
            cmd += ['-i', str(p)]
        inputs = []
        for i in range(1, len(audio) + 1):
            inputs.append(f'[{i}:a]apad,atrim=duration={duration}[a{i}]')
        labels = ''.join(f'[a{i}]' for i in range(1, len(audio) + 1))
        filter_complex = ';'.join(inputs) + f';{labels}amix=inputs={len(audio)}:duration=longest:dropout_transition=0[a]'
        cmd += ['-filter_complex', filter_complex, '-map', '0:v:0', '-map', '[a]']
    else:
        cmd += ['-map', '0:v:0']
    cmd += ['-t', str(duration), '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)]
    _run(cmd)
    return out
