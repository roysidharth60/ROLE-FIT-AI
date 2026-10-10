from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.catalog import list_projects, search_projects
from app.db import init_db
from app.models import CatalogProject, Requirement


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # make sure the tables exist whenever the server starts
    yield


app = FastAPI(title="RoleFit AI API", version="0.1.0", lifespan=lifespan)

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


@app.post("/api/dev/check-requirement")
def check_requirement(req: Requirement):
    """Temporary learning endpoint: shows Pydantic validation. We delete it later."""
    return {"valid": True, "requirement": req}