from app.extractor import extract_requirements
from app.profile_generator import generate_ideal_profile

JD = """Harbor Light Clinics (sample, invented)
Harbor Light runs 14 outpatient clinics and needs an analyst to turn appointment and billing data into weekly reports for clinic managers.
Must have: 2+ years of SQL (window functions, joins on large tables); strong Excel skills; experience building dashboards in Power BI or Tableau; ability to explain findings to non-technical managers.
Good to have: Python (pandas) for data cleaning; knowledge of healthcare data privacy basics; experience with before-and-after analysis of process changes.
We are a friendly, ambitious team looking for someone with great attitude and attention to detail. Hybrid work, 3 days in the office."""

STACKS = [
    ["SQL", "Excel", "Python (pandas)", "Power BI"],
    ["SQL", "Python (pandas)", "Tableau", "Excel"],
    ["SQL", "Excel", "Power BI"],
]

reqs, warnings, _ = extract_requirements(JD)
print("Requirements:", [r.id for r in reqs], "| warnings:", warnings)

profile, issues, usage = generate_ideal_profile(JD, reqs, STACKS, employer_name="Harbor Light Clinics")

print("\nTitle  :", profile.target_title)
print("Summary:", profile.summary)
for group in profile.skill_groups:
    print(f"  {group.label}: {', '.join(group.items)}")
print("\nIssues :", [(i.severity, i.message) for i in issues])
print("Usage  :", usage)