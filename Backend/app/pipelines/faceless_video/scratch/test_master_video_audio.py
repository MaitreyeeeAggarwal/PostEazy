import subprocess
import sys
from pathlib import Path

backend_dir = Path(r"c:\development\SiH\PostEazy\Backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.pipelines.faceless_video.assets.tts import TTSEngine
from app.pipelines.faceless_video.mix.audio import mix_master_audio

work_dir = backend_dir / "work" / "test_master"
work_dir.mkdir(parents=True, exist_ok=True)

wav1 = str(work_dir / "scene_001.wav")
wav2 = str(work_dir / "scene_002.wav")

tts = TTSEngine()
tts.synth_scene_with_timestamps("Welcome to Local AI Desktop Browser!", wav1)
tts.synth_scene_with_timestamps("Your privacy-first browser powered by local LLMs.", wav2)

master_audio = str(work_dir / "master_audio.wav")
mix_master_audio([wav1, wav2], music_wav=None, output_audio=master_audio)

# Probe master audio
cmd_probe = [
    "ffprobe", "-v", "error",
    "-show_entries", "stream=codec_name,sample_rate,channels",
    "-of", "default=noprint_wrappers=1",
    master_audio
]
res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
print("Master Audio Stream Probe:")
print(res.stdout)

print("SUCCESS! Master audio stream verified.")
