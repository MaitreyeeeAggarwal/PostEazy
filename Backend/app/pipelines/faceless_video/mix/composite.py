import subprocess
from pathlib import Path
from app.core.ir import SceneSpec


def composite_scene(bg_mp4: str, text_mov: str, scene_idx: int, work_dir: str = "work", overwrite: bool = True) -> str:
    """Composites background footage and kinetic typography MOV overlay into a scene MP4."""
    out_dir = Path(work_dir) / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"scene_{scene_idx:03d}.mp4"

    if out_mp4.exists() and not overwrite:
        return str(out_mp4)

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,vignette=PI/4,eq=saturation=0.85:brightness=-0.04:contrast=1.05,fps=30,settb=1/30000[bg];"
        "[bg][1:v]overlay=0:0:format=auto,fps=30,settb=1/30000[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_mp4,
        "-i", text_mov,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "30", "-crf", "18", "-preset", "veryfast",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_mp4)
