import asyncio
import json
import shutil
from typing import Optional, Dict, Any

def check_ffmpeg_available() -> bool:
    """Check if ffmpeg and ffprobe are installed and available on PATH."""
    return (shutil.which("ffmpeg") is not None) and (shutil.which("ffprobe") is not None)

async def get_media_duration(file_path: str) -> float:
    """Get exact duration of an audio or video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {file_path}: {stderr.decode()}")
    
    data = json.loads(stdout.decode())
    duration_str = data.get("format", {}).get("duration", "0")
    return float(duration_str)
