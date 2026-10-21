"""Heading names -> one canonical section key.

This is the "synonym dictionary". To teach the app a new heading, add it to
the right list below. Nothing else needs to change.
"""
import re
from difflib import get_close_matches

SYNONYMS = {
    "summary": [
        "professional summary", "summary", "profile", "profile summary",
        "career summary", "objective", "career objective", "about me", "about",
    ],
    "skills": [
        "skills", "technical skills", "key skills", "core skills",
        "core competencies", "skills and tools", "tools and technologies",
        "technologies",
    ],
    "work": [
        "work experience", "professional experience", "experience",
        "employment history", "employment", "work history",
        "project experience", "past experience", "relevant experience",
        "career history",
    ],
    "projects": [
        "projects", "personal projects", "key projects", "selected projects",
        "project work", "past projects",
    ],
    "academic_projects": [
        "academic project", "academic projects", "academic work",
        "university projects", "college projects",
    ],
    "education": [
        "education", "academic background", "education and certifications",
        "qualifications", "academic qualifications",
    ],
    "certifications": [
        "certifications", "certificates", "licenses and certifications",
        "courses", "training",
    ],
    "achievements": [
        "achievements", "awards", "honors", "accomplishments",
        "awards and achievements",
    ],
}

# When a source section has no exact twin in the template, suggest these.
COMPATIBLE = {
    "academic_projects": ["projects"],
    "projects": ["academic_projects", "work"],
    "work": ["projects"],
}

_LOOKUP = {name: key for key, names in SYNONYMS.items() for name in names}


def normalize(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical(text: str) -> str | None:
    """'Past Projects' -> 'projects'. Returns None if we do not recognise it."""
    norm = normalize(text)
    if not norm:
        return None
    if norm in _LOOKUP:
        return _LOOKUP[norm]
    close = get_close_matches(norm, _LOOKUP.keys(), n=1, cutoff=0.85)
    return _LOOKUP[close[0]] if close else None