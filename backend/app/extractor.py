import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.models import Requirement, RequirementList

SYSTEM_PROMPT = (
    "You extract requirements from a job description. Rules:\n"
    "1) Never invent requirements. Use only what the text says.\n"
    "2) Number IDs R1, R2, R3 in order.\n"
    "3) importance comes from the section an item sits under: 'mandatory' for Required, Must have, "
    "Essential or Minimum; 'preferred' for Nice to have, Good to have, Plus or Preferred. Lines under "
    "neither label that only describe the job or the culture are 'preferred' with is_ambiguous true.\n"
    "4) Split lists into one requirement per item (for example, items separated by semicolons).\n"
    "5) source_quote: copy ONE contiguous piece of the job description word-for-word, WITHOUT any section "
    "label such as 'Must have:' or 'Good to have:'.\n"
    "6) Do not extract working conditions (location, hybrid or remote work, office days, salary, benefits, "
    "hours) or descriptions of the company as requirements.\n"
    "7) If a requirement is vague or cannot be checked on a CV, set is_ambiguous to true and write a SPECIFIC "
    "ambiguity_note saying what is unclear and what the employer could clarify (for example, a number, a tool "
    "or a level)."
)

CONDITION_PHRASES = (
    "hybrid", "remote work", "work from home", "in the office", "on-site", "onsite",
    "salary", "benefits", "relocation", "days in office",
)


class ExtractionError(Exception):
    """The model answered, but not in a usable shape."""


def _norm(text: str) -> str:
    """Lowercase, straighten curly quotes, collapse whitespace, so quote matching is fair."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return " ".join(text.lower().split())


def _quote_found(quote: str, jd_norm: str) -> bool:
    """Contiguous quote, or quote once its 'Label:' prefix is removed, or pieces split by '...'."""
    q = _norm(quote)
    if q in jd_norm:
        return True
    if ":" in q:
        tail = q.split(":", 1)[1].strip()
        if tail and tail in jd_norm:
            return True
    parts = [p.strip() for p in re.split(r"\.\.\.|\u2026", q) if p.strip()]
    return len(parts) > 1 and all(p in jd_norm for p in parts)


def check_requirements(jd_text: str, reqs: list[Requirement]) -> tuple[list[Requirement], list[str]]:
    """Deterministic checks. Returns (clean requirements, warnings for the employer)."""
    warnings: list[str] = []
    jd_norm = _norm(jd_text)

    kept: list[Requirement] = []
    for r in reqs:
        if not _quote_found(r.source_quote, jd_norm):
            warnings.append(
                f"Removed '{r.text}': its source quote was not found in the job description."
            )
            continue
        if any(phrase in _norm(f"{r.text} {r.source_quote}") for phrase in CONDITION_PHRASES):
            warnings.append(
                f"Removed '{r.text}': it is a working condition, not a skill the candidate must show."
            )
            continue
        kept.append(r)

    # Renumber so IDs are always R1, R2, R3... with no gaps
    clean = [r.model_copy(update={"id": f"R{i}"}) for i, r in enumerate(kept, start=1)]

    for r in clean:
        if r.importance == "mandatory" and r.is_ambiguous:
            warnings.append(
                f"{r.id} is marked mandatory but is vague. Confirm with the employer "
                "whether it is truly required."
            )

    if not clean:
        warnings.append("No requirements could be verified against the job description.")
    elif not any(r.importance == "mandatory" for r in clean):
        warnings.append("No mandatory requirements were found. Check the job description.")

    return clean, warnings


def extract_requirements(jd_text: str) -> tuple[list[Requirement], list[str], dict | None]:
    """Ask the model for requirements, then verify them in code."""
    structured = get_llm().with_structured_output(RequirementList, include_raw=True)
    result = structured.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=jd_text)]
    )

    if result["parsed"] is None:
        raise ExtractionError(f"The model's answer did not match the schema: {result['parsing_error']}")

    clean, warnings = check_requirements(jd_text, result["parsed"].requirements)
    usage = dict(result["raw"].usage_metadata) if result["raw"].usage_metadata else None
    return clean, warnings, usage