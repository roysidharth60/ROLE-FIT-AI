from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.models import Requirement, RequirementList

SYSTEM_PROMPT = (
    "You extract requirements from a job description. Rules:\n"
    "1) Never invent requirements. Use only what the text says.\n"
    "2) Number IDs R1, R2, R3 in order.\n"
    "3) importance is 'mandatory' ONLY when the text explicitly says required, must, "
    "essential, needed or a minimum. Use 'preferred' for nice-to-have, plus, bonus or "
    "preferred items.\n"
    "4) If a line only describes the job or the culture and says neither, set importance to "
    "'preferred' and is_ambiguous to true.\n"
    "5) source_quote must be copied word-for-word from the job description.\n"
    "6) If a requirement is vague or cannot be checked on a CV, set is_ambiguous to true and "
    "write a SPECIFIC ambiguity_note saying what is unclear and what the employer could "
    "clarify (for example, a number, a tool or a level)."
)


class ExtractionError(Exception):
    """The model answered, but not in a usable shape."""


def _norm(text: str) -> str:
    """Lowercase, straighten curly quotes, collapse whitespace, so quote matching is fair."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return " ".join(text.lower().split())


def check_requirements(jd_text: str, reqs: list[Requirement]) -> tuple[list[Requirement], list[str]]:
    """Deterministic checks. Returns (clean requirements, warnings for the employer)."""
    warnings: list[str] = []
    jd_norm = _norm(jd_text)

    kept: list[Requirement] = []
    for r in reqs:
        if _norm(r.source_quote) not in jd_norm:
            warnings.append(
                f"Removed '{r.text}': its source quote was not found in the job description."
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