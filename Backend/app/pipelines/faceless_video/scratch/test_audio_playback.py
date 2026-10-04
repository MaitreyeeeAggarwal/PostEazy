import os
import sys
import wave
import numpy as np
from pathlib import Path

backend_dir = Path(r"c:\development\SiH\PostEazy\Backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.pipelines.assets.tts import TTSEngine
from app.pipelines.faceless_video.mix.audio import mix_master_audio

def analyze_wav(wav_path: str):
    with wave.open(wav_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        frames = wf.readframes(n_frames)
        
        dtype = np.int16 if sampwidth == 2 else np.int32
        data = np.frombuffer(frames, dtype=dtype)
        max_amp = np.max(np.abs(data)) if len(data) > 0 else 0
        mean_amp = np.mean(np.abs(data)) if len(data) > 0 else 0
        dur = n_frames / float(framerate)
        return {
            "channels": n_channels,
            "framerate": framerate,
            "duration_s": dur,
            "max_amplitude": max_amp,
            "mean_amplitude": mean_amp
        }

print("=== Testing TTS Synthesis & Audio Mix ===")

work_dir = backend_dir / "work" / "test_audio"
work_dir.mkdir(parents=True, exist_ok=True)

# 1. Test TTS synthesis
tts = TTSEngine()
wav1 = str(work_dir / "scene_001.wav")
wav2 = str(work_dir / "scene_002.wav")

text1 = "Welcome to Local AI Desktop Browser!"
text2 = "It processes all AI prompts locally on your device GPU."

print(f"Synthesizing TTS Scene 1: '{text1}'")
dur1, bounds1 = tts.synth_scene_with_timestamps(text1, wav1)
print(f"  -> Duration: {dur1:.2f}s, Timestamps: {len(bounds1)} words")
stats1 = analyze_wav(wav1)
print(f"  -> WAV stats: {stats1}")

print(f"Synthesizing TTS Scene 2: '{text2}'")
dur2, bounds2 = tts.synth_scene_with_timestamps(text2, wav2)
print(f"  -> Duration: {dur2:.2f}s, Timestamps: {len(bounds2)} words")
stats2 = analyze_wav(wav2)
print(f"  -> WAV stats: {stats2}")

# 2. Test Audio Mixing without Music
master_no_music = str(work_dir / "master_no_music.wav")
mix_master_audio([wav1, wav2], music_wav=None, output_audio=master_no_music)
stats_master1 = analyze_wav(master_no_music)
print(f"\nMaster Audio (No Music) stats: {stats_master1}")

# 3. Test Audio Mixing WITH Music (if dummy music created)
dummy_music = str(work_dir / "music.wav")
import subprocess
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=150:duration=10",
    "-c:a", "pcm_s16le", dummy_music
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

master_with_music = str(work_dir / "master_with_music.wav")
mix_master_audio([wav1, wav2], music_wav=dummy_music, output_audio=master_with_music)
stats_master2 = analyze_wav(master_with_music)
print(f"Master Audio (With Music) stats: {stats_master2}")

assert stats1["max_amplitude"] > 1000, "TTS Scene 1 audio is silent!"
assert stats2["max_amplitude"] > 1000, "TTS Scene 2 audio is silent!"
assert stats_master1["max_amplitude"] > 1000, "Master audio is silent!"
print("\nALL AUDIO TESTS PASSED! Audio is generated with clear amplitude.")
