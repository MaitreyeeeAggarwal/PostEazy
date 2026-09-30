from typing import List
from core.ir import DocIR, SceneSpec


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

    # 4. Text Repetition Check (Soft)
    for i in range(len(scenes) - 2):
        w1 = set(scenes[i].narration.lower().split())
        w2 = set(scenes[i+1].narration.lower().split())
        w3 = set(scenes[i+2].narration.lower().split())
        common = w1.intersection(w2).intersection(w3)
        # Filter common stopwords
        content_common = [w for w in common if len(w) > 4]
        if content_common:
            warnings.append(f"Word '{content_common[0]}' repeated across 3 consecutive scenes ({i+1}, {i+2}, {i+3}).")

    passed = len(errors) == 0
    return QCCheckResult(passed=passed, errors=errors, warnings=warnings)
