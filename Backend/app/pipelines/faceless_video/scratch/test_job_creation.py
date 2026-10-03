import sys
import asyncio
from pathlib import Path

backend_dir = Path(r"c:\development\SiH\PostEazy\Backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas import Platform
from app.pipelines.faceless_video.router import run_video_job_pipeline
from app.jobs import job_store

async def test_job_flow():
    print("=== Testing Video Job Pipeline Execution ===")
    
    # Create sample document file
    doc_path = backend_dir / "work" / "test_pipeline_doc.txt"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        "Local AI Desktop Browser processes all prompts on your device GPU. "
        "No data leaves your local machine. Privacy-first fast browsing."
    )

    job = job_store.create_job(pipeline="faceless_video", initial_stage="test_created")
    job_id = job.job_id
    print(f"Created Job ID: {job_id}")

    brand_kit_dict = {
        "logo_path": None,
        "primary_color": None,
        "secondary_color": None,
        "badge_color": None,
        "company_name": "PostEazy Studio",
        "tagline": None,
        "show_end_card": False
    }

    print("Running video job pipeline...")
    await run_video_job_pipeline(
        job_id=job_id,
        file_path=str(doc_path),
        platform=Platform.INSTAGRAM,
        duration_seconds=15,
        typography_option=1,
        song_option=1,
        script_json=None,
        brand_kit=brand_kit_dict,
        style_template_key="bold_creator"
    )

    updated_job = job_store.get_job(job_id)
    print(f"\nFinal Job Status: {updated_job.status}")
    print(f"Final Job Stage:  {updated_job.stage}")
    print(f"Final Progress:   {updated_job.progress}%")
    if updated_job.error:
        print(f"Job Error: {updated_job.error}")
    
    assert updated_job.status.value == "done", f"Job failed with status {updated_job.status}"
    print("\nSUCCESS! Video job pipeline completed 100% successfully.")

if __name__ == "__main__":
    asyncio.run(test_job_flow())
