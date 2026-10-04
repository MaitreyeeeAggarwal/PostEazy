"""Optional PptxGenJS renderer for more art-directed editable slide decks."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.schemas import PresentationDeckScript


def render_creative_pptx(deck: PresentationDeckScript, output_path: str) -> bool:
    """Render with PptxGenJS when the Node creative renderer is installed.

    Returns ``False`` when Node dependencies are unavailable so callers can use
    the native python-pptx renderer without failing a presentation job.
    """
    backend_dir = Path(__file__).resolve().parents[4]
    renderer_dir = backend_dir / "creative_renderer"
    script_path = renderer_dir / "render-presentation.mjs"
    if not shutil.which("node") or not script_path.exists() or not (renderer_dir / "node_modules" / "pptxgenjs").exists():
        return False

    with tempfile.TemporaryDirectory(prefix="posteazy-pptx-") as temp_dir:
        input_path = Path(temp_dir) / "deck.json"
        input_path.write_text(json.dumps(deck.model_dump(mode="json")), encoding="utf-8")
        result = subprocess.run(
            ["node", str(script_path), "--input", str(input_path), "--output", str(output_path)],
            cwd=str(renderer_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            print(f"[Creative PPTX Renderer Warning] {result.stderr[-500:]}")
            return False
    return Path(output_path).exists() and Path(output_path).stat().st_size > 0
