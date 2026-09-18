"""Web application for prr-readiness: upload a change doc, get a PRR readiness report.

Assessment and rubric-normalization both call an LLM and can take tens of
seconds, so both are run as background jobs: the submit endpoint returns a
job id immediately, and the frontend polls the job status endpoint until
it's done.

Run with: uvicorn prr_readiness.web:app --reload
Or:       prr-readiness-web (installed via the `web` extra)
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from arch_compliance import extractors
from arch_compliance.evaluator import evaluate
from arch_compliance.llm import DEFAULT_MODEL
from arch_compliance.rubric import RubricItem, load_rubric, normalize_standards
from arch_compliance.scorer import score

from . import report as report_mod
from .default_rubric import DEFAULT_RUBRIC
from .gate import decide

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="PRR Readiness")

JobStatus = Literal["pending", "running", "done", "error"]


@dataclass
class Job:
    status: JobStatus = "pending"
    kind: str = ""
    result: dict | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}
_jobs_lock = Lock()


def _new_job(kind: str) -> str:
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = Job(status="pending", kind=kind)
    return job_id


def _set_job(job_id: str, **fields) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        for key, value in fields.items():
            setattr(job, key, value)


def _get_job(job_id: str) -> Job:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return job


async def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    suffix = Path(upload.filename or "").suffix
    dest = dest_dir / f"{uuid.uuid4().hex}{suffix}"
    data = await upload.read()
    dest.write_bytes(data)
    return dest


def _run_assess(job_id: str, change_path: Path, rubric_path: Path | None, model: str) -> None:
    _set_job(job_id, status="running")
    try:
        rubric: list[RubricItem] = load_rubric(str(rubric_path)) if rubric_path else DEFAULT_RUBRIC
        change = extractors.extract(change_path, render_images=True)
        results = evaluate(change, rubric, model=model)
        readiness_report = score(rubric, results)
        gate = decide(rubric, results)
        result = {
            "change_source": Path(change.source).name,
            "markdown": report_mod.to_markdown(readiness_report, gate, change.source),
            "json": _json_safe(report_mod.to_json(readiness_report, gate, change.source)),
        }
        _set_job(job_id, status="done", result=result)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        _set_job(job_id, status="error", error=str(exc))
    finally:
        change_path.unlink(missing_ok=True)
        if rubric_path:
            rubric_path.unlink(missing_ok=True)


def _run_normalize(job_id: str, input_paths: list[Path], model: str) -> None:
    _set_job(job_id, status="running")
    try:
        docs = [extractors.extract(p, render_images=False) for p in input_paths]
        items = normalize_standards(docs, model=model)
        result = {
            "rubric": [
                {
                    "id": i.id,
                    "requirement": i.requirement,
                    "category": i.category,
                    "mandatory": i.mandatory,
                    "weight": i.weight,
                }
                for i in items
            ]
        }
        _set_job(job_id, status="done", result=result)
    except Exception as exc:  # noqa: BLE001
        _set_job(job_id, status="error", error=str(exc))
    finally:
        for p in input_paths:
            p.unlink(missing_ok=True)


def _json_safe(text: str) -> dict:
    return json.loads(text)


@app.post("/api/assess")
async def api_assess(
    change: UploadFile = File(...),
    rubric: UploadFile | None = File(None),
    model: str = Form(DEFAULT_MODEL),
):
    tmp_dir = Path(tempfile.mkdtemp(prefix="prr-"))
    change_path = await _save_upload(change, tmp_dir)
    rubric_path = await _save_upload(rubric, tmp_dir) if rubric is not None else None

    job_id = _new_job("assess")
    asyncio.get_running_loop().create_task(
        run_in_threadpool(_run_assess, job_id, change_path, rubric_path, model)
    )
    return {"job_id": job_id}


@app.post("/api/normalize-criteria")
async def api_normalize_criteria(
    files: list[UploadFile] = File(...),
    model: str = Form(DEFAULT_MODEL),
):
    tmp_dir = Path(tempfile.mkdtemp(prefix="prr-norm-"))
    paths = [await _save_upload(f, tmp_dir) for f in files]

    job_id = _new_job("normalize")
    asyncio.get_running_loop().create_task(
        run_in_threadpool(_run_normalize, job_id, paths, model)
    )
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def api_job_status(job_id: str):
    job = _get_job(job_id)
    return {
        "status": job.status,
        "kind": job.kind,
        "result": job.result,
        "error": job.error,
    }


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "prr_readiness.web:app",
        host=os.environ.get("PRR_WEB_HOST", "0.0.0.0"),
        port=int(os.environ.get("PRR_WEB_PORT", "8000")),
        reload=bool(os.environ.get("PRR_WEB_RELOAD")),
    )


if __name__ == "__main__":
    main()
