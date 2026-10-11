from pathlib import Path

from app.docx_export import export_with_checks
from app.cv_builder import build_reference_cv
from app.models import IdealProfileDraft, ReferenceProject, Requirement


def project(pid, kind, title, stack, bullets, readiness=None):
    return ReferenceProject(
        id=pid, kind=kind, title=title,
        scenario="A sample situation used only to test the CV builder.",
        stack=stack, constraints=["Sample constraint"],
        architecture="Sample architecture used only for testing.",
        cv_bullets=bullets, metrics=[], readiness_statement=readiness,
        evidence_signals=["one", "two", "three", "four", "five"],
        covers_requirement_ids=["R1", "R2"],
    )


projects = [
    project("P1", "work", "Weekly Appointment Reports Automated", ["SQL", "Excel", "Python (pandas)", "Power BI"],
            ["Automated data extraction from SQL databases using Python scripts, cutting manual entry from 11 to 2.2 hours per week (-80%).",
             "Cleaned and merged appointment data using Python (pandas), cutting preparation from 8 to 2.4 hours per week (-70%)",
             "Built Power BI dashboards that replaced a weekly Excel pack, cutting refresh time from 95 to 21 minutes (-78%)"]),
    project("P2", "work", "Billing Discrepancies Traced with SQL", ["SQL", "Python (pandas)", "Tableau", "Excel"],
            ["Wrote SQL queries to extract and clean billing data, cutting extraction from 12 to 3.6 hours per week (-70%)",
             "Cross-checked billing against appointments in Python (pandas), cutting errors from 49 to 11 per week (-78%)",
             "Built Tableau dashboards of billing trends, cutting manager questions from 18 to 7 per week (-61%)"]),
    project("P3", "academic", "Exploring Appointment Trends in Public Healthcare Data", ["SQL", "Excel", "Power BI"],
            ["Wrote SQL queries to extract and clean a public healthcare dataset",
             "Built Power BI dashboards of appointment and billing trends"],
            "Built to show SQL, Excel and dashboard skills for the data analyst role."),
]

profile = IdealProfileDraft.model_validate({
    "target_title": "Data Analyst",
    "summary": "Analyzes appointment and billing data using SQL, Excel, and Power BI. "
    "Supports clinic managers with weekly reports and dashboards.",
    "skill_groups": [
        {"label": "Data Analysis", "items": ["SQL", "Excel", "Power BI", "Tableau"]},
        {"label": "Communication", "items": ["Explain Findings", "Report Writing"]},
    ],
})

reqs = [
    Requirement(id="R1", text="2+ years of SQL", importance="mandatory", source_quote="2+ years of SQL"),
    Requirement(id="R2", text="Strong Excel skills", importance="mandatory", source_quote="strong Excel skills"),
    Requirement(id="R3", text="Dashboards in Power BI or Tableau", importance="mandatory", source_quote="dashboards in Power BI or Tableau"),
]

print("--- Case 1: everything covered ---")
cv = build_reference_cv(profile, projects, reqs)
for item in cv.checklist:
    print(("PASS" if item.passed else "FAIL"), "|", item.id, "|", item.detail)
print("First bullet after cleaning:", cv.projects[0].cv_bullets[0])

print("\n--- Case 2: a mandatory requirement the CV never mentions ---")
reqs.append(Requirement(id="R4", text="Kubernetes administration", importance="mandatory", source_quote="Kubernetes administration"))
cv2 = build_reference_cv(profile, projects, reqs)
for item in cv2.checklist:
    print(("PASS" if item.passed else "FAIL"), "|", item.id, "|", item.detail)



print("\n--- Case 3: real DOCX file ---")
data, full_cv = export_with_checks(build_reference_cv(profile, projects, reqs[:3]))
out = Path(__file__).resolve().parent / "data" / "sample_cv.docx"
out.write_bytes(data)
print("Saved:", out, "|", len(data), "bytes")
for item in full_cv.checklist:
    print(("PASS" if item.passed else "FAIL"), "|", item.id, "|", item.detail)


