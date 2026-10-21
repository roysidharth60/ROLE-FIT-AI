from app.cv_builder import build_reference_cv
from app.docx_export import export_with_checks
from app.extractor import extract_requirements
from app.profile_generator import generate_ideal_profile, merge_profile
from app.project_generator import generate_single_project, plan_job

JD = """Harbor Light Clinics (sample, invented)
Harbor Light runs 14 outpatient clinics and needs an analyst to turn appointment and billing data into weekly reports for clinic managers.
Must have: 2+ years of SQL (window functions, joins on large tables); strong Excel skills; experience building dashboards in Power BI or Tableau; ability to explain findings to non-technical managers.
Good to have: Python (pandas) for data cleaning; knowledge of healthcare data privacy basics; experience with before-and-after analysis of process changes.
We are a friendly, ambitious team looking for someone with great attitude and attention to detail. Hybrid work, 3 days in the office."""

ORDER = ["P1", "P2", "P3"]


def show(project, issues, attempts, usage):
    print(f"\n{project.id}: {project.title}  [{project.kind}]  attempts={attempts}  usage={usage}")
    print("  stack:", ", ".join(project.stack))
    for bullet in project.cv_bullets:
        print("   -", bullet)
    print("  issues:", [i.message for i in issues] or "none")


reqs, _, _ = extract_requirements(JD)
premise_plan, coverage, _ = plan_job(JD, reqs)
print("Employer:", premise_plan.employer_name)
print("Premises:", [p.title for p in premise_plan.premises])
print("Coverage:", coverage)

projects = {}
for i, pid in enumerate(ORDER):
    others = [projects[k] for k in ORDER[:i]]
    result = generate_single_project(
        JD, reqs, pid, premise_plan.premises[i], premise_plan.employer_name, coverage[pid], others
    )
    projects[pid] = result[0]
    show(*result)

print("\n=== Employer asks to regenerate P2 with a note ===")
note = "Focus on billing disputes between the clinics and the central billing office, and use Tableau instead of Power BI."
result = generate_single_project(
    JD, reqs, "P2", premise_plan.premises[1], premise_plan.employer_name, coverage["P2"],
    [projects["P1"], projects["P3"]], employer_note=note,
)
projects["P2"] = result[0]
show(*result)

print("\n=== Profile, then regenerate only the summary ===")
stacks = [p.stack for p in projects.values()]
profile, _, _ = generate_ideal_profile(JD, reqs, stacks, premise_plan.employer_name)
print("Summary 1:", profile.summary)
again, _, _ = generate_ideal_profile(
    JD, reqs, stacks, premise_plan.employer_name, employer_note="Mention clinic managers and weekly reporting."
)
merged = merge_profile(profile, again, "summary")
print("Summary 2:", merged.summary)
print("Skills unchanged:", merged.skill_groups == profile.skill_groups)

print("\n=== CV rebuilt from the current parts (no model call) ===")
_, cv = export_with_checks(build_reference_cv(merged, [projects[k] for k in ORDER], reqs))
for item in cv.checklist:
    print(("PASS" if item.passed else "FAIL"), "|", item.id)