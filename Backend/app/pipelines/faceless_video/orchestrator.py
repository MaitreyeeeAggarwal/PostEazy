import json
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from app.pipelines.faceless_video.core.cache import ContentCache
from app.pipelines.faceless_video.core.hashing import hash_stage_input
from app.services.ingest import load_document
from app.pipelines.faceless_video.distil.claims import extract_claims
from app.pipelines.faceless_video.plan.arc import plan_narrative_arc
from app.pipelines.faceless_video.compile.scenes import compile_scenes
from app.pipelines.faceless_video.assets.tts import TTSEngine
from app.pipelines.faceless_video.assets.align import align_scene_audio
from app.pipelines.faceless_video.assets.stock import StockAssetFetcher
from app.pipelines.faceless_video.assets.music import MusicManager
from app.pipelines.faceless_video.assets.ledger import LicenseLedger
from app.pipelines.faceless_video.render.ffmpeg import render_scene_typography_mov
from app.pipelines.faceless_video.mix.composite import composite_scene
from app.pipelines.faceless_video.mix.audio import mix_master_audio
from app.pipelines.faceless_video.mix.export import export_deliverable
from app.pipelines.faceless_video.qc.checks import run_quality_gates
from app.core.brand import BrandKit, StyleTemplate, STYLE_TEMPLATES



class PipelineOrchestrator:
    def __init__(self, work_dir: str = "work", draft_mode: bool = False):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cache = ContentCache(str(self.work_dir / "cache"))
        self.draft_mode = draft_mode
        self.ledger = LicenseLedger(str(self.work_dir / "credits.txt"))

    def _update_progress(self, job_id: Optional[str], stage: str, progress: int, script_data: Optional[dict] = None):
        if not job_id:
            return
        try:
            from app.jobs import job_store
            from app.schemas import JobState
            job_store.update_job(
                job_id,
                status=JobState.RUNNING,
                stage=stage,
                progress=progress,
                script=script_data
            )
        except Exception as e:
            print(f"[Orchestrator Progress Warning] {e}", flush=True)

    def run_pipeline(
        self,
        input_file: str,
        target_seconds: float = 60.0,
        preset: str = "shorts",
        review_pause: bool = False,
        from_stage: int = 1,
        tts_voice: Optional[str] = None,
        theme: str = "neon",
        brand_kit: Optional[BrandKit] = None,
        style_template_key: str = "bold_creator",
        song_option: int = 1,
        job_id: Optional[str] = None
    ) -> str:
        """Executes the 8-stage doc2video compilation DAG pipeline."""
        start_time = time.time()
        print(f"=== Starting doc2video Pipeline: {input_file} ({target_seconds}s target, voice={tts_voice or 'default'}, template={style_template_key}, song=#{song_option}) ===")

        # Stage 1: Ingest
        print("[Stage 1/8] Ingesting document...")
        self._update_progress(job_id, "Stage 1/8: Ingesting document...", 12)
        doc = load_document(input_file)
        print(f"  -> Retained {len(doc.blocks)} content blocks for doc '{doc.title}'.")

        # Stage 2: Distil
        print("[Stage 2/8] Distilling claims...")
        self._update_progress(job_id, "Stage 2/8: Distilling claims & metrics...", 25)
        claims = extract_claims(doc)
        print(f"  -> Extracted {len(claims)} high-salience claims.")

        # Stage 3: Narrative Plan
        print("[Stage 3/8] Planning narrative script arc...")
        self._update_progress(job_id, "Stage 3/8: Planning narrative script arc...", 38)
        beats = plan_narrative_arc(claims, target_seconds=target_seconds)
        print(f"  -> Built script arc with {len(beats)} beats.")

        # Stage 4: Compile Scenes
        print("[Stage 4/8] Compiling shot list & SceneSpecs...")
        self._update_progress(job_id, "Stage 4/8: Compiling visual scene specs...", 50)
        scenes = compile_scenes(beats, claims, brand_kit=brand_kit)
        print(f"  -> Compiled {len(scenes)} visual scenes.")

        script_summary = {
            "title": doc.title,
            "scenes": [{"narration": s.narration, "on_screen_text": getattr(s, "on_screen_text", s.narration[:30])} for s in scenes]
        }
        self._update_progress(job_id, "Stage 4/8: Visual scene specs compiled", 52, script_data=script_summary)

        # Human Review Edit Point (--review flag)
        scenes_json_path = self.work_dir / doc.doc_id / "scenes.json"
        scenes_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache.save_json("compile", doc.doc_id, scenes)

        if review_pause:
            print(f"\n[REVIEW MODE] Pausing pipeline. Edit scene specs at:\n  -> {scenes_json_path.resolve()}\n")
            return str(scenes_json_path)

        # Stage 5: Acquire Assets (TTS, Alignment, Stock, Music)
        print("[Stage 5/8] Acquiring assets (TTS audio, alignment, stock video, music)...")
        self._update_progress(job_id, f"Stage 5/8: Acquiring TTS & stock video assets (Song #{song_option})...", 55)
        doc_work_dir = self.work_dir / doc.doc_id
        doc_work_dir.mkdir(parents=True, exist_ok=True)

        tts = TTSEngine()
        stock_fetcher = StockAssetFetcher(str(doc_work_dir / "assets"))
        
        scene_wavs = []
        bg_mp4s = []

        total_scenes = len(scenes)
        for idx, scene in enumerate(scenes, 1):
            # 5.1 Voice TTS
            wav_path = doc_work_dir / "audio" / f"scene_{scene.idx:03d}.wav"
            _, tts_bounds = tts.synth_scene_with_timestamps(scene.narration, str(wav_path), voice=tts_voice)
            scene_wavs.append(str(wav_path))

            # 5.2 Forced alignment
            align_scene_audio(scene, str(wav_path), tts_bounds=tts_bounds)

            # 5.3 Stock Video Background
            bg_path = stock_fetcher.fetch_background(scene.bg_query, scene.idx, scene.duration_s)
            bg_mp4s.append(bg_path)
            
            # Record in ledger
            self.ledger.record_asset(f"bg_{scene.idx}", "local/procedural", "MIT", "doc2video engine", bg_path)

            pct = 55 + int((idx / max(1, total_scenes)) * 10)
            self._update_progress(job_id, f"Stage 5/8: Fetched assets for scene {idx}/{total_scenes}", pct)

        # 5.4 Music
        total_dur = sum(s.duration_s for s in scenes)
        music_mgr = MusicManager(str(doc_work_dir / "assets"))
        music_wav = music_mgr.get_background_music(total_dur, song_option=song_option)
        self._update_progress(job_id, "Stage 5/8: Assets acquired & background music prepared", 65)

        # Stage 6: Render Typography MOV per scene (Parallelized across scenes)
        print("[Stage 6/8] Rendering kinetic typography MOV alpha scenes in parallel...")
        self._update_progress(job_id, f"Stage 6/8: Rendering typography MOV alpha (Template: {style_template_key})...", 70)
        fps = 24 if self.draft_mode else 30
        style_tmpl = STYLE_TEMPLATES.get(style_template_key, STYLE_TEMPLATES["bold_creator"])
        import concurrent.futures
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    render_scene_typography_mov,
                    scene,
                    fps,
                    str(doc_work_dir),
                    1080,
                    1920,
                    theme,
                    brand_kit,
                    style_tmpl
                ) for scene in scenes
            ]
            text_movs = [f.result() for f in futures]
        self._update_progress(job_id, "Stage 6/8: Kinetic typography alpha overlays rendered", 78)

        # Stage 7: Composite Scene MP4s
        print("[Stage 7/8] Compositing video layers per scene...")
        self._update_progress(job_id, "Stage 7/8: Compositing video layers per scene...", 80)
        scene_mp4s = []
        for idx, (scene, bg_p, text_p) in enumerate(zip(scenes, bg_mp4s, text_movs), 1):
            s_mp4 = composite_scene(bg_p, text_p, scene.idx, work_dir=str(doc_work_dir))
            scene_mp4s.append(s_mp4)
            pct = 80 + int((idx / max(1, total_scenes)) * 10)
            self._update_progress(job_id, f"Stage 7/8: Composited video layer for scene {idx}/{total_scenes}", pct)

        # Quality Gates Check
        print("[Quality Gates] Running automated quality checks...")
        qc = run_quality_gates(doc, scenes)
        if qc.warnings:
            for w in qc.warnings:
                print(f"  [QC WARNING]: {w}")

        # Stage 8: Audio Mix & Master Deliverable Export
        print("[Stage 8/8] Mixing audio (-14 LUFS) and exporting master MP4...")
        self._update_progress(job_id, "Stage 8/8: Mixing audio & exporting master MP4...", 95)
        master_audio = mix_master_audio(scene_wavs, music_wav, output_audio=str(doc_work_dir / "master_audio.wav"))
        
        output_mp4 = self.work_dir / f"master_{preset}.mp4"
        export_deliverable(
            scene_mp4s=scene_mp4s,
            master_audio=master_audio,
            output_mp4=str(output_mp4),
            preset=preset,
            doc_hash=doc.doc_id,
            manifest_data={"total_scenes": len(scenes), "duration_s": total_dur, "title": doc.title},
            scenes=scenes
        )

        elapsed = time.time() - start_time
        print(f"\nSUCCESS! Video generated in {elapsed:.1f}s -> {output_mp4.resolve()}")
        self._update_progress(job_id, "Master Video deliverable generated successfully", 98)
        return str(output_mp4)
