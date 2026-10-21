"""Applicant CV builder API. Kept separate from the employer endpoints."""
import logging
import re
import shutil
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel

from .analyzer import analyze
from .leftovers import find_leftovers
from .pdf import PdfError, docx_to_pdf_bytes
from .render import render_docx
from .starter_preset import build_starter

router = APIRouter(prefix="/api/applicant", tags=["applicant"])

# backend/data/applicant_sessions/<session_id>/info.docx + template.docx
SESSIONS_DIR = Path(__file__).resolve().parents[2] / "data" / "applicant_sessions"
MAX_BYTES = 10 * 1024 * 1024
KEEP_SECONDS = 24 * 3600
PROFILE_DIR = SESSIONS_DIR.parent / "libreoffice_profile"   # LibreOffice's private settings folder
SESSION_RE = re.compile(r"^[0-9a-f]{12}$")


def _cleanup_old_sessions():
    if not SESSIONS_DIR.exists():
        return
    for folder in SESSIONS_DIR.iterdir():
        if folder.is_dir() and time.time() - folder.stat().st_mtime > KEEP_SECONDS:
            shutil.rmtree(folder, ignore_errors=True)


async def _save(upload: UploadFile, nice_name: str, target: Path):
    if not (upload.filename or "").lower().endswith(".docx"):
        raise HTTPException(400, f"The {nice_name} file must be a Word .docx file (not .doc or .pdf).")
    data = await upload.read()
    if not data:
        raise HTTPException(400, f"The {nice_name} file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(400, f"The {nice_name} file is larger than 10 MB.")
    if not data.startswith(b"PK"):
        raise HTTPException(400, f"The {nice_name} file is not a valid .docx file.")
    target.write_bytes(data)


@router.post("/analyze")
async def analyze_files(info: UploadFile = File(...), template: UploadFile = File(...)):
    """Save both files, then return placeholders (from the template) and chips."""
    _cleanup_old_sessions()
    session_id = uuid4().hex[:12]
    folder = SESSIONS_DIR / session_id
    folder.mkdir(parents=True, exist_ok=True)
    info_path, template_path = folder / "info.docx", folder / "template.docx"
    await _save(info, "information", info_path)
    await _save(template, "template", template_path)
    try:
        result = analyze(info_path, template_path)
    except ValueError as err:
        raise HTTPException(400, str(err))
    except Exception:
        raise HTTPException(400, "One of the files could not be read. Please check that both are valid Word documents.")
    result["session_id"] = session_id
    result["filenames"] = {"info": info.filename, "template": template.filename}
    return result


# ---------------- Step 2: build the CV ----------------

def _session_files(session_id: str):
    if not SESSION_RE.match(session_id):
        raise HTTPException(400, "Invalid session id.")
    folder = SESSIONS_DIR / session_id
    info, template = folder / "info.docx", folder / "template.docx"
    if not (info.exists() and template.exists()):
        raise HTTPException(404, "Your uploaded files have expired (they are kept for 24 hours). Please upload them again.")
    return folder, info, template


@router.get("/starter-preset/{session_id}")
def starter_preset(session_id: str):
    """The hand-made mapping (handoff B7) built from this session's two files."""
    _, info, template = _session_files(session_id)
    try:
        return build_starter(analyze(info, template))
    except Exception:
        raise HTTPException(500, "The suggested mapping could not be built for these files.")


class RenderRequest(BaseModel):
    session_id: str
    mapping: dict


@router.post("/render")
def render_cv(
    body: RenderRequest,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    strict: bool = Query(False),
):
    """Fill the template with the mapping and return the CV as a PDF or a DOCX.

    strict=true (used by the download buttons): refuse to deliver a CV that still contains
    placeholder text such as {{W1_COMPANY}} or [COMPANY].
    """
    folder, _, template = _session_files(body.session_id)
    tmp_docx = folder / f"render_{uuid4().hex[:8]}.docx"
    try:
        try:
            render_docx(template, body.mapping, tmp_docx)
        except Exception as err:
            logging.exception("render_docx failed")
            raise HTTPException(500, f"The CV could not be built: {err}")
        if strict:
            left = find_leftovers(tmp_docx)
            if left:
                raise HTTPException(
                    422,
                    "The CV still contains placeholder text: " + ", ".join(left[:5])
                    + ". Remove or replace it before downloading.",
                )
        if format == "docx":
            return Response(
                tmp_docx.read_bytes(),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": 'attachment; filename="CV.docx"'},
            )
        try:
            pdf = docx_to_pdf_bytes(tmp_docx, PROFILE_DIR)
        except PdfError as err:
            logging.error("PDF conversion failed: %s", err)
            raise HTTPException(503, str(err))
        except Exception as err:   # never let an unexpected error drop the connection
            logging.exception("PDF conversion crashed")
            raise HTTPException(500, f"The PDF preview failed: {type(err).__name__}: {err}")
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": 'inline; filename="CV.pdf"'})
    finally:
        tmp_docx.unlink(missing_ok=True)