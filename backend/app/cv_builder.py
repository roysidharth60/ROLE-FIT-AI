from app.models import ChecklistItem, IdealProfileDraft, ReferenceCV, ReferenceProject, Requirement
from app.project_rules import _words

MAX_CV_WORDS = 480  # a rough fit for one A4/Letter page with normal margins
HEADER_WORDS = 15  # name, contact line and section headings


def _clean_bullet(text: str) -> str:
    """One consistent style: no trailing full stop."""
    return text.strip().rstrip(".").strip()


def _cv_text(cv: ReferenceCV) -> str:
    parts = [cv.target_title, cv.summary]
    for group in cv.skill_groups:
        parts.append(group.label)
        parts.extend(group.items)
    for p in cv.projects:
        parts.append(p.title)
        parts.extend(p.stack)
        parts.append(p.scenario)  # printed as "Problem tackled" / "Question explored"
        parts.append(p.architecture)  # printed as "How it was built"
        parts.extend(p.cv_bullets)
        parts.append(p.readiness_statement or "")
    return " ".join(parts)


def run_checklist(cv: ReferenceCV, requirements: list[Requirement]) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []

    # 1. Every clear mandatory requirement appears somewhere on the CV
    cv_words = _words(_cv_text(cv))
    missing = []
    for req in requirements:
        if req.importance == "mandatory" and not req.is_ambiguous:
            terms = _words(req.text)
            if terms and not (terms & cv_words):
                missing.append(req.id)
    items.append(ChecklistItem(
        id="skill_coverage",
        label="Every mandatory requirement is reflected on the CV",
        passed=not missing,
        detail="All mandatory requirements found." if not missing else f"Not found on the CV: {', '.join(missing)}",
    ))

    # 2. Rough one-page estimate
    total = len(_cv_text(cv).split()) + HEADER_WORDS
    items.append(ChecklistItem(
        id="one_page_estimate",
        label="Length looks right for one page (estimate)",
        passed=total <= MAX_CV_WORDS,
        detail=f"About {total} words (limit {MAX_CV_WORDS}). This is an estimate, not a page measurement.",
    ))

    # 3. Bullet style is consistent
    bullets = [b for p in cv.projects for b in p.cv_bullets]
    bad = [b[:30] for b in bullets if not b[:1].isupper() or b.endswith((".", "!", "?"))]
    items.append(ChecklistItem(
        id="bullet_style",
        label="Bullets start with a capital letter and use one consistent ending",
        passed=not bad,
        detail=f"{len(bullets)} bullets checked." if not bad else f"Inconsistent: {bad}",
    ))

    # 4. Placeholders instead of an invented identity
    placeholders = cv.candidate_name.startswith("[") and cv.contact_line.startswith("[") and cv.education_note.startswith("[")
    items.append(ChecklistItem(
        id="no_invented_identity",
        label="Name, contact and education are placeholders, not invented",
        passed=placeholders,
        detail="Placeholders in brackets." if placeholders else "A real-looking identity was found.",
    ))

    # 5. Every project carries its illustrative label
    unlabeled = [p.id for p in cv.projects if "Illustrative" not in p.label]
    items.append(ChecklistItem(
        id="labelled_examples",
        label="Every project is labelled as an illustrative example",
        passed=not unlabeled,
        detail="All projects labelled." if not unlabeled else f"Missing label: {unlabeled}",
    ))
    return items


def build_reference_cv(
    profile: IdealProfileDraft,
    projects: list[ReferenceProject],
    requirements: list[Requirement],
) -> ReferenceCV:
    """Assemble the CV from verified parts. The AI wrote only the profile; Python does the rest."""
    cleaned = [p.model_copy(update={"cv_bullets": [_clean_bullet(b) for b in p.cv_bullets]}) for p in projects]
    cv = ReferenceCV(
        target_title=profile.target_title,
        summary=profile.summary,
        skill_groups=profile.skill_groups,
        projects=cleaned,
    )
    return cv.model_copy(update={"checklist": run_checklist(cv, requirements)})