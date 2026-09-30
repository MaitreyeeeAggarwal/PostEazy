import os
import shutil
import subprocess
from pathlib import Path
from core.ir import SceneSpec
from render.frames import render_frame


def render_scene_typography_mov(scene: SceneSpec, fps: int = 30, work_dir: str = "work", width: int = 1080, height: int = 1920) -> str:
    """Renders PIL RGBA frames and streams raw bytes directly into FFmpeg stdin for fast transparent .mov encoding."""
    scenes_dir = Path(work_dir) / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    out_mov = scenes_dir / f"text_{scene.idx:03d}.mov"
    if out_mov.exists():
        return str(out_mov)

    total_frames = max(1, int(scene.duration_s * fps))

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "png",
        str(out_mov)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for frame_idx in range(total_frames):
            t = frame_idx / float(fps)
            img = render_frame(scene, t, width=width, height=height)
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        proc.wait()
    except Exception as err:
        proc.kill()
        raise err

    return str(out_mov)
