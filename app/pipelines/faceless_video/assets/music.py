from pathlib import Path
import numpy as np
import soundfile as sf


class MusicManager:
    def __init__(self, media_dir: str = "work/assets"):
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def get_background_music(self, total_duration_s: float) -> str:
        """Returns path to background music track fitted to total video duration."""
        music_path = self.media_dir / "bg_music.wav"
        if music_path.exists():
            return str(music_path)

        # Generate ambient background music track (sine pulse chord loop)
        sample_rate = 22050
        num_samples = int(sample_rate * total_duration_s)
        t = np.linspace(0, total_duration_s, num_samples, False)
        
        # Subtle ambient chords (A minor: 220Hz, 261Hz, 329Hz) with 0.5Hz rhythmic swell
        swell = 0.5 * (1 + np.sin(2 * np.pi * 0.5 * t))
        audio = 0.05 * swell * (np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 164.81 * t) + 0.3 * np.sin(2 * np.pi * 220 * t))

        # Fade in/out
        fade_len = int(sample_rate * 1.5)
        audio[:fade_len] *= np.linspace(0, 1, fade_len)
        audio[-fade_len:] *= np.linspace(1, 0, fade_len)

        sf.write(str(music_path), audio, sample_rate)
        return str(music_path)
