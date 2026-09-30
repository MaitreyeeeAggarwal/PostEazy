import asyncio
import os
import subprocess
import wave
import math
import numpy as np
from pathlib import Path
from typing import Optional

class TTSEngine:
    def __init__(self, default_voice: str = "en-US-AvaNeural"):
        self.default_voice = os.getenv("TTS_VOICE", default_voice)

    def synth_scene(self, text: str, output_wav: str, voice: Optional[str] = None) -> float:
        """Synthesizes text into WAV audio file and returns duration in seconds."""
        dur, _ = self.synth_scene_with_timestamps(text, output_wav, voice=voice)
        return dur

    def synth_scene_with_timestamps(
        self, text: str, output_wav: str, voice: Optional[str] = None
    ) -> tuple[float, list[tuple[str, float, float]]]:
        """Synthesizes text into WAV audio file using natural neural voice and returns (duration_s, word_timestamps)."""
        out_path = Path(output_wav)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        word_bounds: list[tuple[str, float, float]] = []

        chosen_voice = voice or self.default_voice

        try:
            import edge_tts
            temp_mp3 = out_path.with_suffix(".mp3")
            
            async def _run():
                communicate = edge_tts.Communicate(text, chosen_voice, rate="+2%")
                with open(temp_mp3, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                            w_text = chunk.get("text", "").strip()
                            offset = chunk.get("offset", 0) / 10000000.0
                            dur = chunk.get("duration", 0) / 10000000.0
                            if w_text:
                                word_bounds.append((w_text, round(offset, 3), round(offset + dur, 3)))
            
            asyncio.run(_run())

            # Convert MP3 to PCM WAV using FFmpeg
            cmd = ["ffmpeg", "-y", "-i", str(temp_mp3), "-ac", "1", "-ar", "24000", str(out_path)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if temp_mp3.exists():
                temp_mp3.unlink()

            duration = self.get_duration(out_path)
            return duration, word_bounds
        except Exception as e:
            print(f"[TTS] edge-tts error: {e}. Generating fallback synthetic speech audio.")
            duration = self._synth_fallback_sine(text, out_path)
            return duration, []

    def get_duration(self, wav_path: Path) -> float:
        """Calculates audio duration in seconds from WAV file header."""
        try:
            import soundfile as sf
            data, sr = sf.read(str(wav_path))
            return len(data) / float(sr)
        except Exception:
            with wave.open(str(wav_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)

    def _synth_fallback_sine(self, text: str, out_path: Path) -> float:
        """Generates a clean synthetic audio tone fallback for testing."""
        num_words = max(1, len(text.split()))
        duration_s = max(1.8, num_words * 0.4)
        sample_rate = 24000

        t = np.linspace(0, duration_s, int(sample_rate * duration_s), False)
        # 220Hz tone modulated by words
        audio = 0.3 * np.sin(2 * np.pi * 220 * t)
        
        # Apply envelope
        fade = int(sample_rate * 0.05)
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)

        import soundfile as sf
        sf.write(str(out_path), audio, sample_rate)
        return duration_s
