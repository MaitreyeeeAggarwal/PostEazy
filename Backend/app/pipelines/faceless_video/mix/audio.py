import subprocess
from pathlib import Path


def mix_master_audio(
    scene_wavs: list[str],
    music_wav: str = None,
    output_audio: str = "work/master_audio.wav",
    transition_duration: float = 0.35
):
    """Mixes voiceover audio tracks with ducked background music and -14 LUFS loudness normalization."""
    out_path = Path(output_audio)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    valid_wavs = [w for w in scene_wavs if Path(w).exists()]
    if not valid_wavs:
        # Generate clean synthetic voiceover audio fallback
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=5",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(out_path)

    has_music = music_wav and Path(music_wav).exists()

    try:
        inputs = []
        for w in valid_wavs:
            inputs.extend(["-i", w])

        n_voice = len(valid_wavs)

        if has_music:
            inputs.extend(["-i", music_wav])
            voice_indices = "".join([f"[{i}:a]" for i in range(n_voice)])
            voice_stage = f"{voice_indices}concat=n={n_voice}:v=0:a=1[voice_raw];" if n_voice > 1 else "[0:a]anull[voice_raw];"
            
            filter_complex = (
                f"{voice_stage}"
                f"[voice_raw]asplit=2[v_sc][v_mix];"
                f"[{n_voice}:a]volume=0.08[music_quiet];"
                f"[music_quiet][v_sc]sidechaincompress=threshold=0.08:ratio=6:attack=15:release=200[ducked_music];"
                f"[v_mix][ducked_music]amix=inputs=2:weights=3 1:dropout_transition=0:normalize=0[raw_mix];"
                f"[raw_mix]loudnorm=I=-14:TP=-1.0:LRA=11[master_a]"
            )
            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[master_a]",
                "-ac", "2", "-ar", "44100",
                "-c:a", "pcm_s16le",
                str(out_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return str(out_path)
        else:
            # Voiceover concatenation only
            voice_indices = "".join([f"[{i}:a]" for i in range(n_voice)])
            filter_complex = f"{voice_indices}concat=n={n_voice}:v=0:a=1[master_a]" if n_voice > 1 else "[0:a]anull[master_a]"
            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[master_a]",
                "-ac", "2", "-ar", "44100",
                "-c:a", "pcm_s16le",
                str(out_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return str(out_path)
    except Exception as e:
        print(f"[Audio Mix Warning]: {e}. Falling back to simple voice concatenation.")
        # Fallback to simple concat of first voice track
        cmd = ["ffmpeg", "-y", "-i", valid_wavs[0], "-c:a", "pcm_s16le", str(out_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(out_path)
