import sys
import asyncio
import concurrent.futures
from pathlib import Path

backend_dir = Path(r"c:\development\SiH\PostEazy\Backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.pipelines.faceless_video.assets.tts import TTSEngine

async def simulate_fastapi_background_task():
    print("=== Simulating FastAPI Background Task Execution ===")
    tts = TTSEngine()
    out_wav = backend_dir / "work" / "debug_tts.wav"
    
    # Run synth_scene_with_timestamps from within active event loop
    print("Calling tts.synth_scene_with_timestamps inside active event loop...")
    dur, bounds = tts.synth_scene_with_timestamps("Hello world this is a test of voice synthesis", str(out_wav))
    print(f"Result -> Duration: {dur:.2f}s, Bounds count: {len(bounds)}")

if __name__ == "__main__":
    asyncio.run(simulate_fastapi_background_task())
