from app.cv_builder import build_reference_cv
from app.docx_export import export_with_checks
from app.extractor import extract_requirements
from app.models import JobDraft
from app.profile_generator import generate_ideal_profile
from app.project_generator import generate_projects


def _add_usage(*usages: dict | None) -> dict:
    total = {"input_tokens": 0, "output_tokens": 0}
    for usage in usages:
        if usage:
            total["input_tokens"] += usage.get("input_tokens", 0)
            total["output_tokens"] += usage.get("output_tokens", 0)
    return total


def generate_job_draft(jd_text: str) -> JobDraft:
    """Job description in, reviewable draft out. Saves nothing."""
    requirements, extraction_warnings, extract_usage = extract_requirements(jd_text)
    projects, project_issues, _attempts, project_usage, plan, employer = generate_projects(jd_text, requirements)
    profile, profile_issues, profile_usage = generate_ideal_profile(
        jd_text, requirements, [p.stack for p in projects], employer
    )

    cv = build_reference_cv(profile, projects, requirements)
    _, cv = export_with_checks(cv)  # adds the checks that need the real DOCX file

    return JobDraft(
        requirements=requirements,
        extraction_warnings=extraction_warnings,
        projects=projects,
        ideal_profile=profile,
        cv=cv,
        issues=project_issues + profile_issues,
        coverage_plan=plan,
        usage=_add_usage(extract_usage, project_usage, profile_usage),
    )