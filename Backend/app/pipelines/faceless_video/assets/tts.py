import asyncio
import os
import subprocess
import wave
import math
import numpy as np
from pathlib import Path
from typing import Optional

SUPPORTED_VOICES = {
    "andrew": "en-US-AndrewNeural",
    "guy": "en-US-GuyNeural",
    "aria": "en-US-AriaNeural",
    "ava": "en-US-AvaMultilingualNeural",
    "brian": "en-US-BrianMultilingualNeural",
    "emma": "en-US-EmmaMultilingualNeural",
    "sonia": "en-GB-SoniaNeural",
    "ryan": "en-GB-RyanNeural",
}

class TTSEngine:
    def __init__(self, default_voice: str = "en-US-AndrewNeural", engine_type: str = "edge_tts"):
        self.default_voice = os.getenv("TTS_VOICE", default_voice)
        self.engine_type = os.getenv("TTS_ENGINE", engine_type)

    def resolve_voice(self, voice_alias_or_name: Optional[str] = None) -> str:
        if not voice_alias_or_name:
            return self.default_voice
        key = voice_alias_or_name.lower().strip()
        return SUPPORTED_VOICES.get(key, voice_alias_or_name)

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

        chosen_voice = self.resolve_voice(voice)

        if not text or not text.strip():
            sample_rate = 24000
            dur = 2.5
            audio = np.zeros(int(sample_rate * dur), dtype=np.float32)
            import soundfile as sf
            sf.write(str(out_path), audio, sample_rate)
            return dur, []

        try:
            import edge_tts
            temp_mp3 = out_path.with_suffix(".mp3")
            
            async def _run():
                communicate = edge_tts.Communicate(text, chosen_voice, rate="+10%")
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        with open(temp_mp3, "ab") as f:
                            f.write(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        w_text = chunk.get("text", "").strip()
                        offset = chunk.get("offset", 0) / 10000000.0
                        dur = chunk.get("duration", 0) / 10000000.0
                        if w_text:
                            word_bounds.append((w_text, round(offset, 3), round(offset + dur, 3)))
            
            # Remove pre-existing temp file if any
            if temp_mp3.exists():
                temp_mp3.unlink()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(lambda: asyncio.run(_run())).result()
            else:
                asyncio.run(_run())

            # Verify temp_mp3 was generated and has non-zero size
            if not temp_mp3.exists() or temp_mp3.stat().st_size == 0:
                raise RuntimeError(f"edge-tts failed to produce MP3 output file at {temp_mp3}")

            # Convert MP3 to PCM WAV using FFmpeg
            cmd = ["ffmpeg", "-y", "-i", str(temp_mp3), "-ac", "1", "-ar", "24000", str(out_path)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if temp_mp3.exists():
                temp_mp3.unlink()

            duration = self.get_duration(out_path)
            return duration, word_bounds
        except Exception as e:
            import traceback
            print(f"[TTS Error Traceback]:")
            traceback.print_exc()
            print(f"[TTS] edge-tts error: {e}. Generating gTTS spoken voiceover fallback.")
            duration = self._synth_fallback_speech(text, out_path)
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

    def _synth_fallback_speech(self, text: str, out_path: Path) -> float:
        """Generates real spoken voiceover narration fallback using gTTS."""
        try:
            import gtts
            temp_mp3 = out_path.with_suffix(".fallback.mp3")
            tts_engine = gtts.gTTS(text=text, lang="en", slow=False)
            tts_engine.save(str(temp_mp3))

            cmd = ["ffmpeg", "-y", "-i", str(temp_mp3), "-ac", "1", "-ar", "24000", str(out_path)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if temp_mp3.exists():
                temp_mp3.unlink()
            return self.get_duration(out_path)
        except Exception as err:
            print(f"[gTTS Fallback Error]: {err}. Falling back to Windows native speech synthesizer.")
            return self._synth_windows_speech(text, out_path)

    def _synth_windows_speech(self, text: str, out_path: Path) -> float:
        """Generates real spoken human voiceover narration using Windows native SpeechSynthesizer."""
        try:
            import base64
            clean_path = str(out_path.resolve()).replace("\\", "/")
            clean_text = text.replace('"', '').replace("'", "").replace("\n", " ")
            ps_script = (
                f"Add-Type -AssemblyName System.Speech\n"
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
                f"$s.SetOutputToWaveFile('{clean_path}')\n"
                f"$s.Speak('{clean_text}')\n"
                f"$s.Dispose()\n"
            )
            enc = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
            subprocess.run(["powershell", "-EncodedCommand", enc], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return self.get_duration(out_path)
        except Exception as err:
            print(f"[Windows SAPI Speech Error]: {err}")
            raise RuntimeError("All TTS voice synthesis engines (edge-tts, gTTS, Windows SAPI) failed.")
