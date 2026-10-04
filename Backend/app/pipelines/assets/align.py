import re
from pathlib import Path
from app.core.ir import SceneSpec, Fragment


def align_scene_audio(scene: SceneSpec, wav_path: str, tts_bounds: list[tuple[str, float, float]] = None) -> SceneSpec:
    """Aligns narration words with synthesized scene audio and updates scene duration."""
    words: list[str] = []
    for frag in scene.fragments:
        words.extend(frag.words)

    if not words:
        words = scene.narration.split()

    from app.pipelines.assets.tts import TTSEngine
    audio_dur = TTSEngine().get_duration(Path(wav_path))

    # Case 1: Match with exact TTS word boundary timestamps if available
    if tts_bounds and len(tts_bounds) >= len(words):
        clean_words_in_scene = [re.sub(r"[^\w%$\-]", "", w).lower() for w in words]
        matched_times = []
        for idx, (w_orig, w_clean) in enumerate(zip(words, clean_words_in_scene)):
            match = next((b for b in tts_bounds if re.sub(r"[^\w%$\-]", "", b[0]).lower() == w_clean), None)
            if match:
                matched_times.append((w_clean, match[1], match[2]))
            elif idx < len(tts_bounds):
                matched_times.append((w_clean, tts_bounds[idx][1], tts_bounds[idx][2]))

        if len(matched_times) == len(words):
            # Trim silent gaps > 0.25s and adjust word timestamps dynamically
            trimmed_times = []
            accumulated_shift = 0.0
            prev_end = 0.0
            
            for word_info in matched_times:
                w_str, w_start, w_end = word_info
                if prev_end > 0:
                    gap = w_start - prev_end
                    if gap > 0.25:
                        excess_gap = gap - 0.18  # Keep tight 0.18s max gap
                        accumulated_shift += excess_gap
                
                adj_start = max(0.0, round(w_start - accumulated_shift, 3))
                adj_end = max(adj_start + 0.08, round(w_end - accumulated_shift, 3))
                trimmed_times.append((w_str, adj_start, adj_end))
                prev_end = w_end

            scene.word_times = trimmed_times
            final_dur = max(audio_dur - accumulated_shift + 0.25, trimmed_times[-1][2] + 0.25)
            scene.duration_s = round(min(scene.max_scene_seconds, final_dur), 2)
            return scene

    # Case 2: Proportional character-weighted alignment
    char_counts = [max(1, len(re.sub(r"[^\w%$\-]", "", w))) for w in words]
    total_chars = max(1, sum(char_counts))
    
    usable_dur = max(1.0, audio_dur - 0.20)
    current_t = 0.08

    word_times: list[tuple[str, float, float]] = []
    for word, c_len in zip(words, char_counts):
        clean_w = re.sub(r"[^\w%$\-]", "", word)
        w_dur = (c_len / float(total_chars)) * usable_dur
        start_t = round(current_t, 3)
        end_t = round(current_t + w_dur * 0.95, 3)
        word_times.append((clean_w, start_t, end_t))
        current_t += w_dur

    scene.word_times = word_times
    scene.duration_s = round(audio_dur + 0.35, 2)
    return scene
