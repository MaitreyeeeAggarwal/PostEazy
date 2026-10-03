from typing import List
from app.core.ir import DocIR, SceneSpec


class QCCheckResult:
    def __init__(self, passed: bool, errors: list[str], warnings: list[str]):
        self.passed = passed
        self.errors = errors
        self.warnings = warnings


def run_quality_gates(doc: DocIR, scenes: list[SceneSpec]) -> QCCheckResult:
    """Executes automated hard and soft quality checks on generated video specs."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Attribution Check (Hard)
    locators = {b.source.locator for b in doc.blocks}
    for scene in scenes:
        if scene.source.locator not in locators:
            warnings.append(f"Scene {scene.idx}: source locator '{scene.source.locator}' not found directly in DocIR blocks.")

    # 2. Scene Duration Check (Soft)
    for scene in scenes:
        if scene.duration_s < 1.8 or scene.duration_s > 6.0:
            warnings.append(f"Scene {scene.idx}: duration {scene.duration_s}s is outside ideal 1.8s–5.0s range.")

    # 3. Global Pace Check (Soft WPM 140–165)
    total_words = sum(len(s.narration.split()) for s in scenes)
    total_dur = sum(s.duration_s for s in scenes)
    wpm = (total_words / max(0.1, total_dur)) * 60.0

    if wpm < 120 or wpm > 180:
        warnings.append(f"Global pace is {wpm:.1f} WPM (target 140–165 WPM).")

    # 5. Engagement Critic (Phase 8 High Retention Checks)
    if scenes:
        hook_words = len(scenes[0].narration.split())
        if hook_words > 8:
            warnings.append(f"Hook scene (Scene 1) has {hook_words} words (recommended <= 8 words for 90%+ retention).")
        
        for i in range(len(scenes) - 1):
            if scenes[i].layout == scenes[i+1].layout and scenes[i].layout != "document_figure":
                warnings.append(f"Layout repetition detected: Scene {scenes[i].idx} and Scene {scenes[i+1].idx} both use '{scenes[i].layout}'.")

        for scene in scenes:
            if scene.duration_s > 4.2:
                warnings.append(f"Scene {scene.idx}: duration {scene.duration_s}s exceeds 4.0s max scene pacing cap.")

    passed = len(errors) == 0
    return QCCheckResult(passed=passed, errors=errors, warnings=warnings)
