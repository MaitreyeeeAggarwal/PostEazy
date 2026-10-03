import sys
from pathlib import Path

backend_dir = Path(r"c:\development\SiH\PostEazy\Backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas import Platform
from app.pipelines.faceless_video.router import generate_document_video_script

# Create a sample text file representing Local AI Desktop Browser document
sample_file = backend_dir / "work" / "test_local_ai_browser.txt"
sample_file.parent.mkdir(parents=True, exist_ok=True)
sample_file.write_text(
    "# Local AI Desktop Browser\n\n"
    "Local AI Desktop Browser is a revolutionary privacy-first web browser powered by local LLMs. "
    "It processes all AI prompts locally on your device GPU with 0 data sent to external servers. "
    "Features include instant offline page summarization, neural web search, and ad-free AI content synthesis."
)

print(f"Testing script generation for file: {sample_file.name}")
script = generate_document_video_script(str(sample_file), sample_file.name, Platform.INSTAGRAM, 30)

print("\n--- GENERATED VIDEO SCRIPT ---")
print("Title:", script.title)
print("Caption:", script.caption)
print("Hashtags:", script.hashtags)
print("\nScenes:")
for idx, sc in enumerate(script.scenes, 1):
    print(f" Scene {idx}:")
    print(f"   Narration: {sc.narration}")
    print(f"   On Screen: {sc.on_screen_text}")
    print(f"   Keywords:  {sc.keywords}")

print("\nSUCCESS! Dynamic script generated directly from document content.")
