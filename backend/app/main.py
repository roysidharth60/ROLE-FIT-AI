from contextlib import asynccontextmanager
from fastapi.responses import Response

from app.docx_export import build_docx
from app.job_builder import generate_job_draft
from app.models import JobDraft, ReferenceCV
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.catalog import list_projects, search_projects
from app.db import init_db
from app.extractor import ExtractionError, extract_requirements
from app.models import (
    CatalogProject,
    ExtractRequest,
    ExtractResponse,
    GenerateResponse,
    Requirement,
)
from app.project_generator import GenerationError, generate_projects

from typing import Literal

from app.jobs_repo import get_job, list_jobs, save_job
from app.models import JobRecord, JobSaveRequest, JobSummary
from app.cv_builder import build_reference_cv
from app.docx_export import export_with_checks
from app.models import (
    BuildCvRequest,
    JobPlan,
    PlanRequest,
    ProfileRequest,
    ProfileResult,
    ProjectRequest,
    ProjectResult,
    BulletsRequest,
    BulletsResult
)
from app.profile_generator import generate_ideal_profile, merge_profile, rewrite_bullets
from app.project_generator import generate_single_project, plan_job
from app.applicant.router import router as applicant_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # make sure the tables exist whenever the server starts
    yield


app = FastAPI(title="RoleFit AI API", version="0.1.0", lifespan=lifespan)

app.include_router(applicant_router)

# Allow the React dev server (Vite) to call this backend during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Tiny check that the server is alive."""
    return {"status": "ok", "app": "RoleFit AI", "version": "0.1.0"}


@app.get("/api/projects", response_model=list[CatalogProject])
def get_projects(
    q: str | None = Query(default=None, max_length=5000, description="Text to match, e.g. a job description"),
    limit: int = Query(default=3, ge=1, le=10),
):
    """List the catalogue, or rank it against the text in q."""
    if q is None or not q.strip():
        return list_projects()
    return search_projects(q, limit)


# @app.post("/api/dev/extract-requirements", response_model=ExtractResponse)
# def dev_extract_requirements(body: ExtractRequest):
#     """Temporary dev endpoint: job description in, verified requirements out."""
#     try:
#         reqs, warnings, usage = extract_requirements(body.jd_text)
#     except ExtractionError as err:
#         raise HTTPException(status_code=502, detail=str(err))
#     except ClientError as err:
#         code = err.response.get("Error", {}).get("Code", "Unknown")
#         raise HTTPException(status_code=502, detail=f"The AI model call failed ({code}).")
#     return ExtractResponse(requirements=reqs, warnings=warnings, usage=usage)


# @app.post("/api/dev/generate-projects", response_model=GenerateResponse)
# def dev_generate_projects(body: ExtractRequest):
#     """Temporary dev endpoint: job description in, requirements + 3 reference projects out."""
#     try:
#         reqs, req_warnings, _ = extract_requirements(body.jd_text)
#         projects, issues, attempts, usage, plan, _employer = generate_projects(body.jd_text, reqs)
#     except (ExtractionError, GenerationError) as err:
#         raise HTTPException(status_code=502, detail=str(err))
#     except ClientError as err:
#         code = err.response.get("Error", {}).get("Code", "Unknown")
#         raise HTTPException(status_code=502, detail=f"The AI model call failed ({code}).")
#     return GenerateResponse(
#         requirements=reqs,
#         extraction_warnings=req_warnings,
#         projects=projects,
#         issues=issues,
#         attempts=attempts,
#         usage=usage,
#         coverage_plan=plan,
#     )


# @app.post("/api/dev/check-requirement")
# def check_requirement(req: Requirement):
#     """Temporary learning endpoint: shows Pydantic validation. We delete it later."""
#     return {"valid": True, "requirement": req}


@app.post("/api/jobs/generate", response_model=JobDraft)
def generate_job(body: ExtractRequest):
    """Job description in, reviewable draft out. Nothing is saved."""
    try:
        return generate_job_draft(body.jd_text)
    except (ExtractionError, GenerationError) as err:
        raise HTTPException(status_code=502, detail=str(err))
    except ClientError as err:
        code = err.response.get("Error", {}).get("Code", "Unknown")
        raise HTTPException(status_code=502, detail=f"The AI model call failed ({code}).")


@app.post("/api/jobs/cv-docx")
def download_cv_docx(cv: ReferenceCV):
    """Build the Word file from the CV the employer has edited."""
    data = build_docx(cv)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="reference_cv.docx"'},
    )


@app.post("/api/jobs", response_model=JobSummary, status_code=201)
def create_job(body: JobSaveRequest):
    """Save the reviewed draft. Publishing needs publish=true AND confirm_publish=true."""
    if body.publish and not body.confirm_publish:
        raise HTTPException(status_code=400, detail="Publishing needs the employer's explicit confirmation (confirm_publish=true).")
    return save_job(body.title, body.draft, publish=body.publish)


@app.get("/api/jobs", response_model=list[JobSummary])
def get_jobs(status: Literal["draft", "published"] | None = None):
    """List jobs, newest first. Page 2 will ask for status=published."""
    return list_jobs(status)


@app.get("/api/jobs/{job_id}", response_model=JobRecord)
def get_one_job(job_id: int):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _ai_errors(func, *args, **kwargs):
    """Run an AI step and turn its failures into a clear 502 for the browser."""
    try:
        return func(*args, **kwargs)
    except (ExtractionError, GenerationError) as err:
        raise HTTPException(status_code=502, detail=str(err))
    except ClientError as err:
        code = err.response.get("Error", {}).get("Code", "Unknown")
        raise HTTPException(status_code=502, detail=f"The AI model call failed ({code}).")


@app.post("/api/jobs/requirements", response_model=ExtractResponse)
def job_requirements(body: ExtractRequest):
    reqs, warnings, usage = _ai_errors(extract_requirements, body.jd_text)
    return ExtractResponse(requirements=reqs, warnings=warnings, usage=usage)


@app.post("/api/jobs/plan", response_model=JobPlan)
def job_plan(body: PlanRequest):
    premise_plan, coverage, usage = _ai_errors(plan_job, body.jd_text, body.requirements)
    return JobPlan(
        employer_name=premise_plan.employer_name,
        premises=premise_plan.premises,
        coverage_plan=coverage,
        usage=usage,
    )


@app.post("/api/jobs/project", response_model=ProjectResult)
def job_project(body: ProjectRequest):
    project, issues, attempts, usage = _ai_errors(
        generate_single_project,
        body.jd_text, body.requirements, body.project_id, body.premise,
        body.employer_name, body.targets, body.others, body.employer_note,
    )
    return ProjectResult(project=project, issues=issues, attempts=attempts, usage=usage)


@app.post("/api/jobs/profile", response_model=ProfileResult)
def job_profile(body: ProfileRequest):
    new, issues, usage = _ai_errors(
        generate_ideal_profile,
        body.jd_text, body.requirements, body.project_stacks, body.employer_name, body.employer_note,
        body.summary_sentences, body.part, body.current,
    )
    return ProfileResult(profile=merge_profile(body.current, new, body.part), issues=issues, usage=usage)


@app.post("/api/jobs/build-cv", response_model=ReferenceCV)
def job_build_cv(body: BuildCvRequest):
    """No AI call: assemble the CV from the current parts and re-run every check on the real file."""
    cv = build_reference_cv(body.profile, body.projects, body.requirements)
    _, cv = export_with_checks(cv)
    return cv


@app.post("/api/jobs/bullets", response_model=BulletsResult)
def job_bullets(body: BulletsRequest):
    bullets, issues, usage = _ai_errors(
        rewrite_bullets, body.kind, body.title, body.scenario, body.stack, body.current_bullets,
        body.employer_note, body.employer_name, body.bullet_count, body.max_words,
    )
    return BulletsResult(bullets=bullets, issues=issues, usage=usage)