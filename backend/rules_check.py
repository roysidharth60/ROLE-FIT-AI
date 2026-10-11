from app.models import ReferenceProject
from app.project_rules import check_project

P1 = {
    "id": "P1", "kind": "work",
    "title": "Shipment-Event Tracking API for a Regional Freight Forwarder",
    "scenario": "A regional freight forwarder updated parcel status from a nightly CSV import, so support agents quoted stale data. Build an event-driven tracking API for scanners and carriers.",
    "stack": ["Python", "FastAPI", "PostgreSQL", "Docker", "GitHub Actions"],
    "constraints": [
        "The existing carrier CSV format must keep working during migration",
        "Tracking lookups must stay under half a second on a 12M-row events table",
    ],
    "architecture": "Carrier and scanner events post to a FastAPI endpoint, are validated, written to PostgreSQL, and read through an indexed tracking query.",
    "cv_bullets": [
        "Replaced a nightly CSV status import with an event-driven FastAPI endpoint, cutting shipment-status delay from 90 minutes to 6 minutes (−93%).",
        "Added composite indexes and rewrote the tracking query on a 12M-row events table, lowering p95 lookup latency from 1.8 s to 0.24 s (−87%).",
        "Containerised the service with Docker and added 74 automated GitHub Actions tests, cutting deploy time from 40 to 9 minutes (−78%).",
    ],
    "metrics": [
        {"name": "shipment-status delay", "unit": "minutes", "baseline": 90, "result": 6, "direction": "decrease"},
        {"name": "p95 tracking lookup latency", "unit": "seconds", "baseline": 1.8, "result": 0.24, "direction": "decrease"},
        {"name": "deploy time", "unit": "minutes", "baseline": 40, "result": 9, "direction": "decrease"},
    ],
    "evidence_signals": [
        "Replaced a batch or scheduled import with an event-driven endpoint",
        "Built REST endpoints with FastAPI, including request validation",
        "Designed or tuned PostgreSQL indexes and queries on a large table",
        "Measured query latency before and after a change",
        "Containerised a Python service with Docker",
        "Set up CI that runs automated tests on every push",
    ],
    "covers_requirement_ids": ["R1", "R2", "R3", "R4", "R6"],
}

P2 = {
    "id": "P2", "kind": "work",
    "title": "Carrier Rate-Quote Service for a Freight Broker",
    "scenario": "A freight broker priced quotes by hand from three spreadsheets, causing slow turnaround and pricing mistakes. Build one quote service with validated rate rules.",
    "stack": ["Python", "Flask", "PostgreSQL", "AWS ECS", "pytest"],
    "constraints": [
        "Rates must be traceable to a carrier tariff version",
        "Quotes must be reproducible for later disputes",
    ],
    "architecture": "A Flask API reads versioned tariff tables from PostgreSQL, applies validated rate rules, and runs as a container on AWS ECS.",
    "cv_bullets": [
        "Consolidated three spreadsheet-based tariff lookups into one Flask quote API, cutting quote turnaround from 25 minutes to 4 minutes (−84%).",
        "Added schema validation and 60 pytest cases for rate rules, lowering quoting errors from 18 to 5 per 1,000 quotes (−72%).",
        "Deployed the service to AWS ECS behind a load balancer, lowering monthly infrastructure spend from 420 to 260 USD (−38%).",
    ],
    "metrics": [
        {"name": "quote turnaround", "unit": "minutes", "baseline": 25, "result": 4, "direction": "decrease"},
        {"name": "quoting errors", "unit": "per 1,000 quotes", "baseline": 18, "result": 5, "direction": "decrease"},
        {"name": "monthly infrastructure spend", "unit": "USD", "baseline": 420, "result": 260, "direction": "decrease"},
    ],
    "evidence_signals": [
        "Built a Flask or FastAPI service that applies business rules to compute a result",
        "Versioned reference data in a SQL database so results can be reproduced",
        "Wrote automated tests for rule edge cases",
        "Deployed a containerised service to AWS (ECS or similar)",
        "Compared error rates or cost before and after a change",
    ],
    "covers_requirement_ids": ["R1", "R2", "R3", "R5"],
}

P3 = {
    "id": "P3", "kind": "academic",
    "title": "Self-Initiated Shipment Tracker (Learning Project)",
    "scenario": "A personal learning project that models parcel-tracking events using a public sample dataset, built to practise the stack used by the hiring team.",
    "stack": ["Python", "FastAPI", "PostgreSQL", "Docker", "pytest"],
    "constraints": ["Uses only public sample data, no real shipment records"],
    "architecture": "A FastAPI service stores shipment events in PostgreSQL and exposes endpoints to add and look up events.",
    "cv_bullets": [
        "Built a FastAPI tracker over a public sample shipment dataset to learn how tracking events are modelled in PostgreSQL.",
        "Wrote a README explaining design trade-offs and tested the main endpoints with pytest, listing what I would change for real traffic.",
    ],
    "metrics": [],
    "readiness_statement": "Built before applying to understand how freight-tracking systems work and to practise the exact stack in this role.",
    "evidence_signals": [
        "Public repository with a README explaining design decisions",
        "FastAPI endpoints to create and query shipment events",
        "PostgreSQL schema with an index justified in the README",
        "Automated pytest tests for the main endpoints",
        "Dockerfile so the project runs with one command",
    ],
    "covers_requirement_ids": ["R1", "R2", "R3", "R4"],
}


def show(project: ReferenceProject) -> None:
    issues = check_project(project)
    print(f"{project.id} [{project.kind}] {project.title}")
    print("  label:", project.label)
    for m in project.metrics:
        print(f"  metric: {m.name}: {m.baseline} -> {m.result} {m.unit} ({m.change_pct}%)")
    if not issues:
        print("  checks: OK")
    for issue in issues:
        print(f"  {issue.severity.upper()}: {issue.message}")
    print()


def main() -> None:
    good = [ReferenceProject.model_validate(d) for d in (P1, P2, P3)]
    print("=== GOOD SAMPLES (expect all OK) ===\n")
    for p in good:
        show(p)

    words = sum(len(b.split()) for p in good for b in p.cv_bullets)
    words += sum(len(p.title.split()) for p in good)
    print(f"CV project text: {words} words (aim for under about 230 to fit one page)\n")

    print("=== BROKEN SAMPLES (expect errors) ===\n")
    bad_work = good[0].model_copy(update={"cv_bullets": [
        good[0].cv_bullets[0],
        "Added composite indexes on the events table, lowering p95 lookup latency from 1.8 s to 240 ms (−90%).",
        good[0].cv_bullets[2],
    ]})
    bad_academic = good[2].model_copy(update={"cv_bullets": [
        "Built a tracker that reduced support cost by 30% for customers.",
        good[2].cv_bullets[1],
    ]})
    show(bad_work)
    show(bad_academic)


if __name__ == "__main__":
    main()