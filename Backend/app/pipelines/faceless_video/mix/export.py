import json
import subprocess
import time
from pathlib import Path
from typing import Optional
from app.core.ir import SceneSpec

PLATFORM_PRESETS = {
    "reels": {"res": "1080x1920", "crf": "20", "bitrate": "8M"},
    "shorts": {"res": "1080x1920", "crf": "19", "bitrate": "10M"},
    "tiktok": {"res": "1080x1920", "crf": "20", "bitrate": "8M"},
    "youtube": {"res": "1920x1080", "crf": "18", "bitrate": "12M"},
    "linkedin": {"res": "1080x1080", "crf": "20", "bitrate": "8M"}
}

TRANSITION_MAP = {
    "fade": "fade",
    "crossfade": "fade",
    "dip": "fadeblack",
    "push": "slideleft",
    "slide": "smoothleft",
    "dissolve": "dissolve",
    "zoom": "zoomin",
    "cut": "fade"
}


def get_video_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 3.5


def export_deliverable(
    scene_mp4s: list[str],
    master_audio: str,
    output_mp4: str = "master.mp4",
    preset: str = "shorts",
    doc_hash: str = "",
    manifest_data: dict = None,
    scenes: Optional[list[SceneSpec]] = None,
    transition_duration: float = 0.35
) -> str:
    """Concatenates composited scene MP4s with smooth xfade transitions, combines audio, applies platform encoding preset, and writes manifest.json."""
    out_path = Path(output_mp4)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    p_config = PLATFORM_PRESETS.get(preset, PLATFORM_PRESETS["shorts"])
    n_scenes = len(scene_mp4s)
    rendered = False

    if n_scenes > 1 and transition_duration > 0:
        try:
            durations = [get_video_duration(s) for s in scene_mp4s]
            
            # Construct single-pass xfade filtergraph with normalized timestamps (PTS-STARTPTS)
            filter_chains = []
            for idx in range(n_scenes):
                filter_chains.append(f"[{idx}:v]fps=30,settb=1/30000,setpts=PTS-STARTPTS[v{idx}]")

            prev_stream = "[v0]"
            cur_dur = durations[0]

            for i in range(1, n_scenes):
                trans_name = scenes[i].transition if scenes and i < len(scenes) else "fade"
                xfade_type = TRANSITION_MAP.get(trans_name, "fade")
                d_trans = min(transition_duration, cur_dur / 2.0, durations[i] / 2.0)
                offset = max(0.1, cur_dur - d_trans)

                out_stream = f"[v_xf{i}]" if i < n_scenes - 1 else "[v_final]"
                filter_chains.append(
                    f"{prev_stream}[v{i}]xfade=transition={xfade_type}:duration={d_trans:.2f}:offset={offset:.2f}{out_stream}"
                )
                prev_stream = out_stream
                cur_dur = offset + durations[i]

            filter_complex_str = ";".join(filter_chains)

            cmd_xfade = ["ffmpeg", "-y"]
            for s_mp4 in scene_mp4s:
                cmd_xfade.extend(["-i", s_mp4])
            cmd_xfade.extend(["-i", master_audio])

            audio_idx = n_scenes

            cmd_xfade.extend([
                "-filter_complex", filter_complex_str,
                "-map", "[v_final]",
                "-map", f"{audio_idx}:a:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "30", "-crf", p_config["crf"], "-preset", "veryfast",
                "-c:a", "aac", "-ac", "2", "-ar", "44100", "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(out_path)
            ])
            subprocess.run(cmd_xfade, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rendered = True
        except Exception as err:
            print(f"[export_deliverable] Single-pass xfade transition build failed: {err}. Falling back to standard concat.")
            rendered = False

    if not rendered:
        concat_list_path = Path("work/concat_list.txt")
        concat_list_path.parent.mkdir(parents=True, exist_ok=True)
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for s_mp4 in scene_mp4s:
                abs_p = Path(s_mp4).resolve().as_posix()
                f.write(f"file '{abs_p}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
            "-i", master_audio,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "30", "-crf", p_config["crf"], "-preset", "veryfast",
            "-c:a", "aac", "-ac", "2", "-ar", "44100", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(out_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. Write manifest.json beside deliverable
    manifest_path = out_path.parent / "manifest.json"
    manifest = {
        "doc_hash": doc_hash,
        "export_preset": preset,
        "target_resolution": p_config["res"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "details": manifest_data or {}
    }
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    return str(out_path)
