"""Optional Remotion post-processing for polished, animated video deliverables."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _duration_seconds(video_path: Path) -> float | None:
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)], capture_output=True, text=True, check=False)
    try:
        return float(probe.stdout.strip())
    except ValueError:
        return None


def enhance_video_with_remotion(video_path: str, title: str) -> str | None:
    """Add an animated Remotion treatment and return its path on success.

    Remotion is optional; a failed browser render leaves the FFmpeg output
    untouched so a completed video job never becomes a failed job.
    """
    source = Path(video_path)
    backend_dir = Path(__file__).resolve().parents[4]
    renderer_dir = backend_dir / "creative_renderer"
    script_path = renderer_dir / "render-video.mjs"
    if not source.exists() or not shutil.which("node") or not script_path.exists() or not (renderer_dir / "node_modules" / "@remotion" / "renderer").exists():
        return None
    duration = _duration_seconds(source)
    if not duration:
        return None
    enhanced = source.with_stem(f"{source.stem}_creative")
    result = subprocess.run(["node", str(script_path), "--source", str(source.resolve()), "--output", str(enhanced), "--title", title, "--duration", str(duration)], cwd=str(renderer_dir), capture_output=True, text=True, timeout=max(180, int(duration * 8)), check=False)
    if result.returncode != 0 or not enhanced.exists() or enhanced.stat().st_size == 0:
        if enhanced.exists():
            enhanced.unlink()
        print(f"[Remotion Renderer Warning] {result.stderr[-500:]}")
        return None
    return str(enhanced)
