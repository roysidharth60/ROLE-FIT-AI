# Hand-written catalogue of ILLUSTRATIVE reference projects.
# Every project and every number below is an invented example, not anyone's real work.

CATALOG_PROJECTS = [
    {
        "title": "Hospital Bed-Occupancy Forecasting API",
        "domain": "Healthcare analytics",
        "description": (
            "A mid-size hospital group needs a 7-day forecast of ward-level bed occupancy so "
            "planners can reassign nursing staff. Build a FastAPI service that trains on two "
            "years of anonymised admission/discharge records and serves forecasts per ward. "
            "Example target: forecast error under 10% on a held-out 4-week window."
        ),
        "skills": ["Python", "FastAPI", "SQL", "Time-series forecasting", "Pandas", "Docker"],
        "difficulty": "intermediate",
        "evidence_signals": [
            "Built a forecasting model on time-series data (admissions, demand or similar)",
            "Backtested on a held-out time window and reported an error metric (MAPE, RMSE)",
            "Exposed predictions through a REST API with a documented request/response schema",
            "Handled missing or irregular timestamps in the source data",
            "Stored raw and cleaned data in a SQL database",
            "Containerised the service with Docker",
        ],
    },
    {
        "title": "Support Assistant for a Regional Courier Company (RAG)",
        "domain": "Logistics customer support",
        "description": (
            "A courier firm wants an assistant that answers 'where is my parcel' and policy "
            "questions using its own tariff PDFs and delivery FAQs, and says 'I don't know' "
            "when the documents do not cover a question. Build retrieval-augmented generation "
            "with source citations and a small evaluation set of 40 example questions."
        ),
        "skills": ["Python", "LangChain", "RAG", "Embeddings", "Prompt engineering", "Evaluation"],
        "difficulty": "advanced",
        "evidence_signals": [
            "Split PDFs or documents into chunks and indexed them for retrieval",
            "Returned answers with citations pointing back to source passages",
            "Implemented a refusal or fallback when retrieval found nothing relevant",
            "Created an evaluation set of questions and measured answer quality",
            "Tuned chunk size, prompt wording or retrieval settings based on results",
            "Used LangChain or a comparable framework for the pipeline",
        ],
    },
    {
        "title": "Invoice Extraction Pipeline with a Human Review Queue",
        "domain": "Back-office automation",
        "description": (
            "A small freight forwarder receives about 300 supplier invoices a week as PDFs. "
            "Build a pipeline that extracts supplier, date, line items and totals into validated "
            "JSON, flags low-confidence or arithmetically inconsistent invoices, and sends them "
            "to a review queue instead of the accounting database."
        ),
        "skills": ["Python", "Pydantic", "PDF parsing", "LLM structured output", "SQL", "Testing"],
        "difficulty": "intermediate",
        "evidence_signals": [
            "Extracted structured fields from PDF or scanned documents",
            "Validated extracted data with a schema (Pydantic or equivalent)",
            "Checked arithmetic consistency (line items sum to total) in code",
            "Routed uncertain results to a human review step instead of auto-accepting",
            "Wrote automated tests using sample documents",
        ],
    },
    {
        "title": "Warehouse Sensor Telemetry Live Dashboard",
        "domain": "Industrial IoT",
        "description": (
            "A cold-storage warehouse has temperature sensors on 40 pallets racks and needs "
            "a live dashboard that highlights racks drifting out of range within 30 seconds. "
            "Build a FastAPI WebSocket feed and a React dashboard with threshold alerts "
            "and a 24-hour history chart."
        ),
        "skills": ["React", "JavaScript", "FastAPI", "WebSockets", "SQL", "Charting"],
        "difficulty": "intermediate",
        "evidence_signals": [
            "Built a React interface that updates live without page refresh",
            "Used WebSockets or server-sent events for streaming data",
            "Implemented threshold-based alerts with visible status indicators",
            "Showed historical data in a chart",
            "Simulated or ingested device or sensor data",
            "Handled disconnects and reconnection in the client",
        ],
    },
    {
        "title": "Rules-Based Fraud Flagging Service for a Mobile Payments Startup",
        "domain": "Fintech risk",
        "description": (
            "A payments startup wants transparent, auditable rules (velocity limits, unusual "
            "device or location changes, repeated failed attempts) that flag suspicious "
            "transactions before any machine learning is used. Build a rules engine where each "
            "flag records which rule fired and why, with a back-test on 100,000 synthetic transactions."
        ),
        "skills": ["Python", "SQL", "Rules engines", "Testing", "Data analysis", "REST APIs"],
        "difficulty": "advanced",
        "evidence_signals": [
            "Implemented configurable business rules separate from application code",
            "Recorded an explanation for every flagged item (which rule, which values)",
            "Back-tested rules against a labelled or synthetic dataset",
            "Reported false-positive and false-negative trade-offs",
            "Wrote unit tests for individual rules and edge cases",
        ],
    },
    {
        "title": "Multi-Tenant Job Board Backend on AWS",
        "domain": "SaaS platform engineering",
        "description": (
            "A recruiting startup needs a backend where each employer sees only its own "
            "jobs and applications. Build a FastAPI service with tenant isolation, a PostgreSQL "
            "or SQLite data layer, Docker packaging, a CI pipeline that runs tests on every push, "
            "and a deployment to AWS with environment-based configuration."
        ),
        "skills": ["Python", "FastAPI", "AWS", "Docker", "CI/CD", "SQL", "Testing"],
        "difficulty": "advanced",
        "evidence_signals": [
            "Enforced per-tenant data isolation in queries or middleware",
            "Used environment variables for configuration, with no secrets in code",
            "Containerised the application with Docker",
            "Set up a CI pipeline that runs automated tests on each push",
            "Deployed to a cloud provider (AWS or similar)",
            "Wrote tests that check one tenant cannot read another tenant's data",
        ],
    },
]