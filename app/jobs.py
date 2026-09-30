import uuid
import datetime
from threading import Lock
from typing import Dict, Optional, Any
from app.schemas import JobStatus, JobState

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
        return job

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        with self._lock:
            return self._jobs.get(job_id)

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
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            now = datetime.datetime.utcnow().isoformat() + "Z"
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
            return job

# Global singleton job store instance
job_store = JobStore()
