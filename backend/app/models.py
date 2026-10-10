from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Requirement(BaseModel):
    """One checkable requirement taken from a job description."""

    id: str = Field(pattern=r"^R\d+$", description="Requirement ID such as R1, R2")
    text: str = Field(min_length=3, max_length=300, description="The requirement in plain words")
    importance: Literal["mandatory", "preferred"]
    source_quote: str = Field(min_length=3, description="Exact words from the job description")
    is_ambiguous: bool = False
    ambiguity_note: str | None = Field(
        default=None, description="Why it is unclear, for employer review"
    )

    @model_validator(mode="after")
    def ambiguous_needs_a_note(self):
        if self.is_ambiguous and not (self.ambiguity_note and self.ambiguity_note.strip()):
            raise ValueError("ambiguity_note is required when is_ambiguous is true")
        return self


    

class CatalogProject(BaseModel):
    """A hand-written illustrative reference project from the catalogue."""

    id: int
    title: str
    domain: str
    description: str
    skills: list[str]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    evidence_signals: list[str]
    score: int = 0  # relevance score, only filled in when searching