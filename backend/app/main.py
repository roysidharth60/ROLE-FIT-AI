from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import Requirement

app = FastAPI(title="RoleFit AI API", version="0.1.0")

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


@app.post("/api/dev/check-requirement")
def check_requirement(req: Requirement):
    """Temporary learning endpoint: shows Pydantic validation. We delete it later."""
    return {"valid": True, "requirement": req}