"""Consistent, safe terminal logging for asynchronous content pipelines."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


LOGGER_NAME = "posteazy.pipeline"


def configure_pipeline_logging(level: str | None = None) -> None:
    """Configure a dedicated terminal logger without modifying Uvicorn logging."""
    logger = logging.getLogger(LOGGER_NAME)
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    elif not logger.handlers:
        logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_pipeline_event(
    pipeline: str,
    event: str,
    *,
    job_id: str | None = None,
    stage: str | None = None,
    progress: int | None = None,
    level: int = logging.INFO,
    **details: Any,
) -> None:
    """Write a compact structured event; never pass source text or credentials."""
    configure_pipeline_logging()
    payload = {key: value for key, value in details.items() if value is not None}
    fields = [
        f"time={datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"pipeline={pipeline}",
        f"event={event}",
    ]
    if job_id:
        fields.append(f"job={job_id}")
    if stage:
        fields.append(f"stage={json.dumps(stage, ensure_ascii=False)}")
    if progress is not None:
        fields.append(f"progress={progress}%")
    if payload:
        fields.append("details=" + json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True))
    logging.getLogger(LOGGER_NAME).log(level, "[PostEazy] " + " ".join(fields))
