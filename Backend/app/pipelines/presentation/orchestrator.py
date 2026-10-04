import asyncio
from pathlib import Path
from typing import Optional
from app.config import settings
from app.schemas import PresentationDeckScript, JobState
from app.jobs import job_store
from app.services.ingest import load_document
from app.pipelines.presentation.core.llm_planner import plan_presentation_deck
from app.pipelines.presentation.render.html_renderer import render_presentation_html
from app.pipelines.presentation.render.pdf_renderer import render_presentation_pdf
from app.pipelines.presentation.render.pptx_renderer import render_presentation_pptx
from app.pipelines.presentation.render.creative_pptx import render_creative_pptx
from app.core.pipeline_logging import log_pipeline_event


async def run_presentation_job_pipeline(
    job_id: str,
    file_path: Optional[str],
    theme: str = "bold_tech",
    script_dict: Optional[dict] = None
):
    try:
        log_pipeline_event("presentation_slides", "pipeline_started", job_id=job_id, theme=theme, source="approved_draft" if script_dict else "source_document")
        job_store.update_job(job_id, status=JobState.RUNNING, stage="Ingesting document...", progress=10)

        out_dir = Path(settings.WORK_DIR) / "jobs" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        if script_dict:
            deck = PresentationDeckScript.model_validate(script_dict)
        else:
            if not file_path:
                raise ValueError("A source document or approved deck script is required.")
            doc = load_document(file_path)
            job_store.update_job(job_id, stage="Synthesizing slide deck outline...", progress=30)
            deck = plan_presentation_deck(doc, theme=theme)

        log_pipeline_event("presentation_slides", "deck_ready", job_id=job_id, slides=len(deck.slides), theme=deck.theme)

        job_store.update_job(job_id, script=deck.model_dump(), stage="Rendering presentation slides...", progress=60)

        # 1. HTML Deliverable
        html_content = render_presentation_html(deck)
        html_path = out_dir / "presentation.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        log_pipeline_event("presentation_slides", "html_rendered", job_id=job_id, output=html_path.name, bytes=html_path.stat().st_size)

        # 2. PDF Deliverable
        pdf_path = out_dir / "presentation.pdf"
        try:
            render_presentation_pdf(deck, str(pdf_path))
            log_pipeline_event("presentation_slides", "pdf_rendered", job_id=job_id, output=pdf_path.name, exists=pdf_path.exists())
        except Exception as pdf_err:
            print(f"[PDF Render Note]: {pdf_err}")
            log_pipeline_event("presentation_slides", "pdf_render_warning", job_id=job_id, level=30, error_summary=str(pdf_err)[:300])

        # 3. PPTX Deliverable
        pptx_path = out_dir / "presentation.pptx"
        try:
            renderer = "pptxgenjs" if render_creative_pptx(deck, str(pptx_path)) else "python-pptx"
            if renderer == "python-pptx":
                render_presentation_pptx(deck, str(pptx_path))
            log_pipeline_event("presentation_slides", "pptx_rendered", job_id=job_id, output=pptx_path.name, exists=pptx_path.exists(), renderer=renderer)
        except Exception as pptx_err:
            print(f"[PPTX Render Note]: {pptx_err}")
            log_pipeline_event("presentation_slides", "pptx_render_warning", job_id=job_id, level=30, error_summary=str(pptx_err)[:300])

        output_urls = {
            "html_url": f"/api/presentation/jobs/{job_id}/download?format=html",
            "pdf_url": f"/api/presentation/jobs/{job_id}/download?format=pdf",
            "pptx_url": f"/api/presentation/jobs/{job_id}/download?format=pptx"
        }

        job_store.update_job(
            job_id,
            status=JobState.DONE,
            stage="Completed",
            progress=100,
            output_urls=output_urls
        )
        log_pipeline_event("presentation_slides", "pipeline_completed", job_id=job_id, output_formats=["html", "pdf", "pptx"])
    except Exception as e:
        import traceback
        print(f"[Presentation Pipeline Error Traceback]:")
        traceback.print_exc()
        log_pipeline_event("presentation_slides", "pipeline_failed", job_id=job_id, level=40, error_summary=str(e)[:300])
        job_store.update_job(job_id, status=JobState.FAILED, stage="error", error=str(e))
