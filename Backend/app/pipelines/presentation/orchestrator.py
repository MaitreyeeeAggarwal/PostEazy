import asyncio
from pathlib import Path
from typing import Optional, Dict
from app.config import settings
from app.schemas import PresentationDeckScript, JobState
from app.jobs import job_store
from app.services.ingest import load_document
from app.pipelines.presentation.core.llm_planner import plan_presentation_deck
from app.pipelines.presentation.render.html_renderer import render_presentation_html
from app.pipelines.presentation.render.pdf_renderer import render_presentation_pdf
from app.pipelines.presentation.render.pptx_renderer import render_presentation_pptx


async def run_presentation_job_pipeline(
    job_id: str,
    file_path: str,
    theme: str = "bold_tech",
    script_dict: Optional[dict] = None
):
    try:
        job_store.update_job(job_id, status=JobState.RUNNING, stage="Ingesting document...", progress=10)

        out_dir = Path(settings.WORK_DIR) / "jobs" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        if script_dict:
            deck = PresentationDeckScript.model_validate(script_dict)
        else:
            doc = load_document(file_path)
            job_store.update_job(job_id, stage="Synthesizing slide deck outline...", progress=30)
            deck = plan_presentation_deck(doc, theme=theme)

        job_store.update_job(job_id, script=deck.model_dump(), stage="Rendering presentation slides...", progress=60)

        # 1. HTML Deliverable
        html_content = render_presentation_html(deck)
        html_path = out_dir / "presentation.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 2. PDF Deliverable
        pdf_path = out_dir / "presentation.pdf"
        try:
            render_presentation_pdf(deck, str(pdf_path))
        except Exception as pdf_err:
            print(f"[PDF Render Note]: {pdf_err}")

        # 3. PPTX Deliverable
        pptx_path = out_dir / "presentation.pptx"
        try:
            render_presentation_pptx(deck, str(pptx_path))
        except Exception as pptx_err:
            print(f"[PPTX Render Note]: {pptx_err}")

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
    except Exception as e:
        import traceback
        print(f"[Presentation Pipeline Error Traceback]:")
        traceback.print_exc()
        job_store.update_job(job_id, status=JobState.FAILED, stage="error", error=str(e))
