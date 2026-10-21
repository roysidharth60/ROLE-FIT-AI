from typing import Literal

from pydantic import BaseModel, Field, model_validator, computed_field


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





class RequirementList(BaseModel):
    """What we ask the AI to return."""

    requirements: list[Requirement]


class ExtractRequest(BaseModel):
    jd_text: str = Field(min_length=50, max_length=20000, description="The job description text")


class ExtractResponse(BaseModel):
    requirements: list[Requirement]
    warnings: list[str]
    usage: dict | None = None  # token counts, handy while developing




class Issue(BaseModel):
    """A problem found by our deterministic checks."""

    severity: Literal["error", "warning"]
    message: str


class Metric(BaseModel):
    """One measured result. Python, not the AI, calculates the percentage."""

    name: str = Field(min_length=3, max_length=80, description="What is measured")
    unit: str = Field(min_length=1, max_length=20)
    baseline: float = Field(gt=0, description="Value before the change")
    result: float = Field(ge=0, description="Value after the change")
    direction: Literal["decrease", "increase"]

    @computed_field
    @property
    def change_pct(self) -> float:
        if self.direction == "decrease":
            change = (self.baseline - self.result) / self.baseline * 100
        else:
            change = (self.result - self.baseline) / self.baseline * 100
        return round(change, 1)


class ReferenceProject(BaseModel):
    """An illustrative reference project. Never presented as a real person's work."""

    id: str = Field(pattern=r"^P\d+$")
    kind: Literal["work", "academic"]
    title: str = Field(min_length=5, max_length=100)
    scenario: str = Field(min_length=20, max_length=400)
    stack: list[str] = Field(min_length=2, max_length=8)
    constraints: list[str] = Field(min_length=1, max_length=4)
    architecture: str = Field(min_length=10, max_length=400)
    cv_bullets: list[str] = Field(min_length=2, max_length=3)
    metrics: list[Metric] = Field(default_factory=list, max_length=3)
    readiness_statement: str | None = Field(default=None, max_length=250)
    evidence_signals: list[str] = Field(min_length=5, max_length=8)
    covers_requirement_ids: list[str] = Field(min_length=1)

    @computed_field
    @property
    def label(self) -> str:
        # Always added by code, never by the AI
        if self.kind == "work":
            return "Illustrative reference project - all figures are examples"
        return "Illustrative academic reference project - example only"


    

class ProjectSet(BaseModel):
    """What we ask the AI to return: exactly three projects."""

    projects: list[ReferenceProject] = Field(min_length=3, max_length=3)


class GenerateResponse(BaseModel):
    requirements: list[Requirement]
    extraction_warnings: list[str]
    projects: list[ReferenceProject]
    issues: list[Issue]  # remaining errors or warnings for employer review
    attempts: int
    usage: dict | None = None
    coverage_plan: dict[str, list[str]] = Field(default_factory=dict)




class MetricPlan(BaseModel):
    """The model proposes a rough metric. Python decides the exact numbers."""

    name: str = Field(min_length=3, max_length=80, description="What is measured")
    unit: str = Field(min_length=1, max_length=20, description="A duration, count, rate per 1,000 or money. Never %")
    direction: Literal["decrease", "increase"]
    baseline_hint: float = Field(gt=0, description="A rough starting value before the change")
    improvement_pct: float = Field(ge=15, le=90, description="Rough improvement, between 15 and 90")


class WorkBulletPlan(BaseModel):
    text: str = Field(
        min_length=20,
        max_length=250,
        description="Use the exact placeholders {baseline}, {result} and {pct} where the numbers go",
    )
    metric: MetricPlan


class WorkDraft(BaseModel):
    """Strict shape for one work project, used only while generating."""

    title: str = Field(min_length=5, max_length=100)
    scenario: str = Field(min_length=20, max_length=400)
    stack: list[str] = Field(min_length=2, max_length=8)
    constraints: list[str] = Field(
        min_length=1,
        max_length=4,
        description="Real-world limits of the situation (data size, deadline, compliance). Not writing instructions.",
    )
    architecture: str = Field(min_length=10, max_length=400)
    bullets: list[WorkBulletPlan] = Field(min_length=3, max_length=3)
    evidence_signals: list[str] = Field(min_length=5, max_length=8)
    covers_requirement_ids: list[str] = Field(min_length=1)


class AcademicDraft(BaseModel):
    """Strict shape for the academic project, used only while generating."""

    title: str = Field(min_length=5, max_length=100)
    scenario: str = Field(min_length=20, max_length=400)
    stack: list[str] = Field(min_length=2, max_length=8)
    constraints: list[str] = Field(
        min_length=1,
        max_length=4,
        description="Real-world limits of the situation (data source, scope). Not writing instructions.",
    )
    architecture: str = Field(min_length=10, max_length=400)
    bullets: list[str] = Field(min_length=2, max_length=3)
    readiness_statement: str = Field(min_length=20, max_length=250)
    evidence_signals: list[str] = Field(min_length=5, max_length=8)
    covers_requirement_ids: list[str] = Field(min_length=1)


class Premise(BaseModel):
    title: str = Field(min_length=5, max_length=100)
    situation: str = Field(min_length=20, max_length=300)


class PremisePlan(BaseModel):
    """Three different starting situations, planned before the projects are written."""

    employer_name: str = Field(default="", max_length=100)
    premises: list[Premise] = Field(min_length=3, max_length=3)

class SkillGroup(BaseModel):
    label: str = Field(min_length=3, max_length=40, description="For example: Data and SQL")
    items: list[str] = Field(min_length=2, max_length=8)


class IdealProfileDraft(BaseModel):
    """What we ask the AI to write: only the parts that need wording."""

    target_title: str = Field(min_length=3, max_length=80, description="The job title this CV is aimed at")
    summary: str = Field(
        min_length=40,
        max_length=800,
        description="1 to 4 sentences, third-person free, about the skills and kind of work. No invented employers.",
    )
    skill_groups: list[SkillGroup] = Field(min_length=2, max_length=4)

class ChecklistItem(BaseModel):
    """One ATS-friendliness check, calculated by Python."""

    id: str
    label: str
    passed: bool
    detail: str


class ReferenceCV(BaseModel):
    """The one-page reference CV. Placeholders are fixed by code, never written by the AI."""

    candidate_name: str = "[Candidate Name]"
    contact_line: str = "[City] | [email] | [phone] | [LinkedIn]"
    target_title: str
    summary: str
    skill_groups: list[SkillGroup] = Field(min_length=2, max_length=4)
    projects: list[ReferenceProject] = Field(min_length=3, max_length=3)
    education_note: str = "[Add your own education and certifications here]"
    checklist: list[ChecklistItem] = Field(default_factory=list)

    @computed_field
    @property
    def label(self) -> str:
        return "Illustrative reference CV - example content only, not a real person"


class JobDraft(BaseModel):
    """Everything the employer reviews on Page 1. Nothing here is saved until they publish."""

    requirements: list[Requirement]
    extraction_warnings: list[str]
    projects: list[ReferenceProject]
    ideal_profile: IdealProfileDraft
    cv: ReferenceCV
    issues: list[Issue]
    coverage_plan: dict[str, list[str]] = Field(default_factory=dict)
    usage: dict | None = None
    employer_name: str = Field(default="", max_length=100)



class JobSaveRequest(BaseModel):
    """What Page 1 sends when the employer saves or publishes the reviewed draft."""

    title: str = Field(min_length=3, max_length=120)
    draft: JobDraft
    publish: bool = False
    confirm_publish: bool = False  # the explicit "yes, publish" from the employer


class JobSummary(BaseModel):
    id: int
    title: str
    status: Literal["draft", "published"]
    created_at: str
    published_at: str | None = None
    employer_name: str = ""


class JobRecord(JobSummary):
    draft: JobDraft



class PlanRequest(BaseModel):
    jd_text: str = Field(min_length=50, max_length=20000)
    requirements: list[Requirement] = Field(min_length=1)


class JobPlan(BaseModel):
    employer_name: str
    premises: list[Premise]
    coverage_plan: dict[str, list[str]]
    usage: dict | None = None


class ProjectRequest(BaseModel):
    jd_text: str = Field(min_length=50, max_length=20000)
    requirements: list[Requirement] = Field(min_length=1)
    project_id: Literal["P1", "P2", "P3"]
    premise: Premise
    employer_name: str = Field(default="", max_length=100)
    targets: list[str]
    others: list[ReferenceProject] = Field(default_factory=list, max_length=2)
    employer_note: str = Field(default="", max_length=300)


class ProjectResult(BaseModel):
    project: ReferenceProject
    issues: list[Issue]
    attempts: int
    usage: dict | None = None


class ProfileRequest(BaseModel):
    jd_text: str = Field(min_length=50, max_length=20000)
    requirements: list[Requirement] = Field(min_length=1)
    project_stacks: list[list[str]] = Field(min_length=1)
    employer_name: str = Field(default="", max_length=100)
    part: Literal["all", "summary", "skills"] = "all"
    current: IdealProfileDraft | None = None
    employer_note: str = Field(default="", max_length=300)
    summary_sentences: int = Field(default=2, ge=1, le=4)

class ProfileResult(BaseModel):
    profile: IdealProfileDraft
    issues: list[Issue]
    usage: dict | None = None


class BuildCvRequest(BaseModel):
    profile: IdealProfileDraft
    projects: list[ReferenceProject] = Field(min_length=3, max_length=3)
    requirements: list[Requirement]



class BulletsRequest(BaseModel):
    project_id: Literal["P1", "P2", "P3"]
    kind: Literal["work", "academic"]
    title: str = Field(min_length=3, max_length=100)
    scenario: str = Field(max_length=400)
    stack: list[str] = Field(default_factory=list)
    current_bullets: list[str] = Field(default_factory=list, max_length=4)
    employer_note: str = Field(min_length=3, max_length=300)
    employer_name: str = Field(default="", max_length=100)
    bullet_count: int = Field(default=3, ge=2, le=3)
    max_words: int = Field(default=30, ge=15, le=45)


class BulletsResult(BaseModel):
    bullets: list[str]
    issues: list[Issue]
    usage: dict | None = None