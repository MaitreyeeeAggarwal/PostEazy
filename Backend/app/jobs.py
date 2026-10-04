import uuid
import datetime
from threading import Lock
from typing import Dict, Optional, Any
from app.schemas import JobStatus, JobState
from app.database import SessionLocal
from app.models import JobModel
from app.core.pipeline_logging import log_pipeline_event


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, JobStatus] = {}
        self._lock = Lock()

    def create_job(self, pipeline: str, initial_stage: str = "initialized") -> JobStatus:
        job_id = uuid.uuid4().hex[:12]
        now = datetime.datetime.utcnow().isoformat() + "Z"
        job = JobStatus(
            job_id=job_id,
            pipeline=pipeline,
            status=JobState.QUEUED,
            stage=initial_stage,
            progress=0,
            created_at=now,
            updated_at=now
        )
        with self._lock:
            self._jobs[job_id] = job
        log_pipeline_event(pipeline, "job_created", job_id=job_id, stage=initial_stage, progress=0)

        # Persist to database if available
        if SessionLocal is not None and JobModel is not None:
            try:
                db = SessionLocal()
                db_job = JobModel(
                    job_id=job_id,
                    pipeline=pipeline,
                    status=JobState.QUEUED.value,
                    stage=initial_stage,
                    progress=0
                )
                db.add(db_job)
                db.commit()
                db.close()
            except Exception as e:
                print(f"[DB Warning] Could not persist job to DB: {e}")

        return job

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        with self._lock:
            job = self._jobs.get(job_id)

        if job:
            return job

        # Check DB fallback
        if SessionLocal is not None and JobModel is not None:
            try:
                db = SessionLocal()
                db_job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
                db.close()
                if db_job:
                    job = JobStatus(
                        job_id=db_job.job_id,
                        pipeline=db_job.pipeline,
                        status=JobState(db_job.status),
                        stage=db_job.stage or "initialized",
                        progress=db_job.progress or 0,
                        created_at=db_job.created_at.isoformat() + "Z" if db_job.created_at else "",
                        updated_at=db_job.updated_at.isoformat() + "Z" if db_job.updated_at else "",
                        error=db_job.error,
                        script=db_job.script_data,
                        output_urls=db_job.output_urls
                    )
                    with self._lock:
                        self._jobs[job_id] = job
                    return job
            except Exception as e:
                print(f"[DB Warning] Could not fetch job from DB: {e}")

        return None

    def update_job(
        self,
        job_id: str,
        status: Optional[JobState] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        script: Optional[Dict[str, Any]] = None,
        output_urls: Optional[Dict[str, str]] = None
    ) -> Optional[JobStatus]:
        now = datetime.datetime.utcnow().isoformat() + "Z"

        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                if status is not None:
                    job.status = status
                if stage is not None:
                    job.stage = stage
                if progress is not None:
                    job.progress = max(0, min(100, progress))
                if error is not None:
                    job.error = error
                if script is not None:
                    job.script = script
                if output_urls is not None:
                    job.output_urls = output_urls
                job.updated_at = now

        # Sync with database if available
        if SessionLocal is not None and JobModel is not None:
            try:
                db = SessionLocal()
                db_job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
                if db_job:
                    if status is not None:
                        db_job.status = status.value if isinstance(status, JobState) else status
                    if stage is not None:
                        db_job.stage = stage
                    if progress is not None:
                        db_job.progress = max(0, min(100, progress))
                    if error is not None:
                        db_job.error = error
                    if script is not None:
                        db_job.script_data = script
                    if output_urls is not None:
                        db_job.output_urls = output_urls
                    db_job.updated_at = datetime.datetime.utcnow()
                    db.commit()
                db.close()
            except Exception as e:
                print(f"[DB Warning] Could not update job in DB: {e}")

        updated_job = job or self.get_job(job_id)
        if updated_job:
            log_pipeline_event(
                updated_job.pipeline,
                "job_updated",
                job_id=job_id,
                stage=stage or updated_job.stage,
                progress=progress if progress is not None else updated_job.progress,
                status=(status.value if isinstance(status, JobState) else status) or updated_job.status.value,
                has_script=script is not None,
                has_outputs=output_urls is not None,
                error_summary=error[:300] if error else None,
            )
        return updated_job


# Global singleton job store instance
job_store = JobStore()
