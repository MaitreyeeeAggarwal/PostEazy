from pathlib import Path
import numpy as np
import soundfile as sf


class MusicManager:
    def __init__(self, media_dir: str = "work/assets"):
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def get_background_music(self, total_duration_s: float, song_option: int = 1) -> str:
        """Returns path to background music track fitted to total video duration."""
        music_path = self.media_dir / f"bg_music_opt{song_option}.wav"
        if music_path.exists():
            return str(music_path)

        sample_rate = 24000
        num_samples = int(sample_rate * max(3.0, total_duration_s))
        t = np.linspace(0, total_duration_s, num_samples, False)

        # Build rhythmic chord progression based on song_option
        if song_option == 2:
            # Cinematic / Driving (D minor chord progression: D2, F2, A2)
            base_freqs = [146.83, 174.61, 220.00]
            bpm = 120
        elif song_option == 3:
            # Upbeat / High Energy (C major chord progression: C3, E3, G3)
            base_freqs = [130.81, 164.81, 196.00]
            bpm = 128
        else:
            # Lofi / Ambient (A minor: 110Hz, 164.81Hz, 220Hz)
            base_freqs = [110.00, 164.81, 220.00]
            bpm = 100

        # Rhythmic pulse (tempo modulation)
        pulse = 0.5 * (1.0 + np.sin(2 * np.pi * (bpm / 60.0) * t))
        audio = pulse * (
            0.5 * np.sin(2 * np.pi * base_freqs[0] * t) +
            0.3 * np.sin(2 * np.pi * base_freqs[1] * t) +
            0.2 * np.sin(2 * np.pi * base_freqs[2] * t)
        )

        # Normalize audio to peak amplitude 0.6 (-4.4 dB FS)
        max_amp = np.max(np.abs(audio))
        if max_amp > 0:
            audio = (audio / max_amp) * 0.6

        # Smooth 1.0s fade in and fade out
        fade_len = min(int(sample_rate * 1.0), num_samples // 4)
        if fade_len > 0:
            audio[:fade_len] *= np.linspace(0, 1, fade_len)
            audio[-fade_len:] *= np.linspace(1, 0, fade_len)

        sf.write(str(music_path), audio, sample_rate)
        return str(music_path)
