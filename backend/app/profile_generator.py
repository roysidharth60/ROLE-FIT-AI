import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.models import IdealProfileDraft, Issue, Requirement
from app.project_generator import MAX_ATTEMPTS, GenerationError, _leaks, _mask
from app.project_rules import _words

PROFILE_SYSTEM = (
    "You write the top part of an illustrative reference CV for a job. Return:\n"
    "- target_title: the job title from the job description.\n"
    "- summary: exactly 2 sentences, at most 55 words, no pronouns (never I, my, we, our). Sentence 1: what this "
    "person does and with which main tools. Sentence 2: the kind of work or outcome they support. Plain words, "
    "no percentages, no money, no company names, no filler like 'passionate', 'results-driven' or 'insights'.\n"
    "- skill_groups: 2 to 4 groups, each with a short label and 2 to 8 short items (at most 40 characters each). "
    "Include EVERY mandatory requirement, using the job description's own wording for tools and skills. "
    "Add the tools listed under TOOLS USED IN THE REFERENCE PROJECTS. Never repeat an item in two groups.\n"
    "Do not invent employers, certifications, degrees or years of experience."
        " Label each group by topic (for example 'Data and SQL', 'Reporting and Dashboards', 'Communication'); "
    "never use labels like 'Preferred' or 'Mandatory'. Write items as noun phrases in normal spelling "
    "('Stakeholder reporting', 'Power BI', 'SQL (window functions, joins)'), not as verbs, and do not add "
    "skills the job description does not mention."
)

_FILLER_WORDS = {
    "utilized", "utilised", "leveraged", "robust", "seamless", "comprehensive",
    "insights", "insightful", "streamlined", "streamlining", "enhanced",
    "passionate", "results-driven", "dynamic", "synergy",
}
_FIRST_PERSON = re.compile(r"\b(?:i|my|me|we|our)\b", re.IGNORECASE)
_MONEY_OR_PERCENT = re.compile(r"[%$€£₹]")


def check_profile(profile: IdealProfileDraft, requirements: list[Requirement], employer_name: str) -> list[Issue]:
    issues: list[Issue] = []
    summary = profile.summary

    words = len(summary.split())
    if words > 60:
        issues.append(Issue(severity="error", message=f"The summary has {words} words (maximum 55)."))
    sentences = len(re.findall(r"[.!?](?:\s|$)", summary))
    if sentences > 3:
        issues.append(Issue(severity="error", message=f"The summary has {sentences} sentences. Use exactly 2."))
    if _FIRST_PERSON.search(summary):
        issues.append(Issue(severity="error", message="The summary must not use I, my, we or our."))
    if _MONEY_OR_PERCENT.search(summary):
        issues.append(Issue(severity="error", message="The summary must not contain percentages or money."))

    all_items = [item for g in profile.skill_groups for item in g.items]
    text = " ".join([profile.target_title, summary] + [g.label for g in profile.skill_groups] + all_items)

    if _leaks(employer_name, text):
        issues.append(Issue(severity="error", message="The profile mentions the employer's name. Remove it."))

    used = sorted(set(re.findall(r"[a-z\-]+", text.lower())) & _FILLER_WORDS)
    if used:
        issues.append(Issue(severity="error", message=f"Replace these filler words with plain wording: {used}"))

    for item in all_items:
        if len(item) > 40:
            issues.append(Issue(severity="error", message=f"Skill item '{item[:30]}...' is longer than 40 characters."))
    lowered = [i.strip().lower() for i in all_items]
    repeats = sorted({i for i in lowered if lowered.count(i) > 1})
    if repeats:
        issues.append(Issue(severity="error", message=f"These skill items appear more than once: {repeats}"))

    covered_words = _words(text)
    for req in requirements:
        if req.importance == "mandatory" and not req.is_ambiguous:
            terms = _words(req.text)
            if terms and not (terms & covered_words):
                issues.append(Issue(
                    severity="error",
                    message=f"{req.id} ('{req.text}') is not reflected in the summary or skills. "
                    "Use the job description's wording.",
                ))
    return issues


def generate_ideal_profile(
    jd_text: str,
    requirements: list[Requirement],
    project_stacks: list[list[str]],
    employer_name: str = "",
):
    """Returns (profile, issues, token usage)."""
    structured = get_llm(1200).with_structured_output(IdealProfileDraft, include_raw=True)

    req_lines = [
        f"{r.id} [{r.importance}{', ambiguous' if r.is_ambiguous else ''}] {r.text}" for r in requirements
    ]
    tools = sorted({tool for stack in project_stacks for tool in stack})
    base = (
        "JOB DESCRIPTION:\n" + _mask(jd_text, employer_name)
        + "\n\nREQUIREMENTS:\n" + "\n".join(req_lines)
        + "\n\nTOOLS USED IN THE REFERENCE PROJECTS: " + ", ".join(tools)
    )

    feedback: list[str] = []
    best = None  # (error count, profile, issues)
    tokens_in = tokens_out = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base
        if feedback:
            prompt += "\n\nYOUR PREVIOUS ATTEMPT HAD THESE PROBLEMS. Fix every one:\n" + "\n".join(
                f"- {m}" for m in feedback
            )
            print(f"[profile] attempt {attempt} retrying because: {feedback}")
        result = structured.invoke([SystemMessage(content=PROFILE_SYSTEM), HumanMessage(content=prompt)])
        usage = result["raw"].usage_metadata or {}
        tokens_in += usage.get("input_tokens", 0)
        tokens_out += usage.get("output_tokens", 0)

        if result["parsed"] is None:
            feedback = [f"Your answer did not match the required format: {str(result['parsing_error'])[:300]}"]
            continue

        profile = result["parsed"]
        issues = check_profile(profile, requirements, employer_name)
        errors = [i for i in issues if i.severity == "error"]
        if best is None or len(errors) < best[0]:
            best = (len(errors), profile, issues)
        if not errors:
            break
        feedback = [i.message for i in errors]

    if best is None:
        raise GenerationError("The model never produced a usable profile.")
    return best[1], best[2], {"input_tokens": tokens_in, "output_tokens": tokens_out}