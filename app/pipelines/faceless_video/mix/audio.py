import subprocess
from pathlib import Path


def mix_master_audio(
    scene_wavs: list[str],
    music_wav: str,
    output_audio: str = "work/master_audio.wav",
    transition_duration: float = 0.35
):
    """Mixes voiceover audio tracks with ducked background music and -14 LUFS loudness normalization."""
    out_path = Path(output_audio)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if len(scene_wavs) == 0:
        raise ValueError("No scene WAV files provided for audio mixing.")

    # 1. Build FFmpeg audio inputs
    inputs = []
    for w in scene_wavs:
        inputs.extend(["-i", w])
    inputs.extend(["-i", music_wav])

    n_voice = len(scene_wavs)
    
    if n_voice == 1 or transition_duration <= 0:
        voice_indices = "".join([f"[{i}:a]" for i in range(n_voice)])
        voice_stage = f"{voice_indices}concat=n={n_voice}:v=0:a=1[voice_raw];"
    else:
        af_parts = []
        prev_label = "[0:a]"
        for i in range(1, n_voice):
            next_input = f"[{i}:a]"
            out_label = "[voice_raw]" if i == n_voice - 1 else f"[a_xf_{i}]"
            af_parts.append(f"{prev_label}{next_input}acrossfade=d={transition_duration:.2f}:c1=tri:c2=tri{out_label}")
            prev_label = out_label
        voice_stage = ";".join(af_parts) + ";"

    filter_complex = (
        f"{voice_stage}"
        f"[voice_raw]asplit=2[v_sc][v_mix];"
        f"[{n_voice}:a]volume=0.15[music_quiet];"
        f"[music_quiet][v_sc]sidechaincompress=threshold=0.05:ratio=8:attack=25:release=280[ducked_music];"
        f"[v_mix][ducked_music]amix=inputs=2:duration=first[raw_mix];"
        f"[raw_mix]loudnorm=I=-14:TP=-1.0:LRA=11[master_a]"
    )

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[master_a]",
        "-c:a", "pcm_s16le",
        str(out_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_path)
