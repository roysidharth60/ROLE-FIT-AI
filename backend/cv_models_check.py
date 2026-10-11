from pydantic import ValidationError

from app.models import IdealProfileDraft, ReferenceCV

good = {
    "target_title": "Data Analyst",
    "summary": "Builds weekly reports from appointment and billing data using SQL, Excel and Power BI. "
    "Cleans data with Python and explains findings to non-technical managers.",
    "skill_groups": [
        {"label": "Data and SQL", "items": ["SQL", "Window functions", "Python (pandas)"]},
        {"label": "Reporting", "items": ["Excel", "Power BI", "Dashboards"]},
    ],
}
bad = {
    "target_title": "Data Analyst",
    "summary": "Too short.",
    "skill_groups": [{"label": "Data", "items": ["SQL"]}],
}

print("GOOD profile:", IdealProfileDraft.model_validate(good).target_title)

try:
    IdealProfileDraft.model_validate(bad)
except ValidationError as err:
    print("BAD profile rejected with", err.error_count(), "problems:")
    for e in err.errors():
        print(" -", ".".join(str(x) for x in e["loc"]), "|", e["msg"])

print("ReferenceCV fields:", list(ReferenceCV.model_fields))