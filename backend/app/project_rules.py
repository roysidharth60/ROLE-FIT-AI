import re

from app.models import Issue, Metric, ReferenceProject, Requirement

MAX_BULLET_WORDS = 30
MIN_IMPROVEMENT_PCT = 10.0
MAX_IMPROVEMENT_PCT = 95.0

_REQ_ID = re.compile(r"^R\d+$")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MONEY_OR_PERCENT = re.compile(r"[%$€£₹]|\b(?:rs|inr|usd|eur)\b", re.IGNORECASE)
_BUSINESS_WORDS = {
    "revenue", "cost", "costs", "saving", "savings", "saved", "profit", "production",
    "customers", "clients", "faster", "reduced", "reduction", "increased", "downtime", "roi",
}


def _err(message: str) -> Issue:
    return Issue(severity="error", message=message)


def _warn(message: str) -> Issue:
    return Issue(severity="warning", message=message)


def _fmt(value: float) -> str:
    """90.0 -> '90', 0.24 -> '0.24', 1.8 -> '1.8'"""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)


def _check_metric(pid: str, n: int, bullet: str, m: Metric) -> list[Issue]:
    issues: list[Issue] = []
    moves_right = m.result < m.baseline if m.direction == "decrease" else m.result > m.baseline
    if not moves_right:
        return [_err(f"{pid} metric {n}: result does not {m.direction} from the baseline.")]

    text = bullet.replace(",", "")
    for value in (m.baseline, m.result):
        if _fmt(value) not in text:
            issues.append(_err(f"{pid} bullet {n} does not mention the number {_fmt(value)}."))

    stated = [float(x) for x in _PERCENT.findall(text)]
    if not any(abs(x - m.change_pct) <= 1.0 for x in stated):
        issues.append(
            _err(f"{pid} bullet {n}: the percentage should be about {m.change_pct}% (found {stated or 'none'}).")
        )

    if not MIN_IMPROVEMENT_PCT <= m.change_pct <= MAX_IMPROVEMENT_PCT:
        issues.append(_warn(f"{pid} bullet {n}: a {m.change_pct}% change may look unrealistic."))
    return issues


def _check_work(p: ReferenceProject) -> list[Issue]:
    if len(p.cv_bullets) != 3 or len(p.metrics) != 3:
        return [_err(
            f"{p.id}: has {len(p.cv_bullets)} bullets and {len(p.metrics)} metrics; a work project "
            "needs exactly 3 of each, one metric (baseline, result, unit, direction) per bullet."
        )]
    issues: list[Issue] = []
    for n, (bullet, metric) in enumerate(zip(p.cv_bullets, p.metrics), start=1):
        if metric.unit.strip().lower() in {"%", "percent", "percentage"}:
            issues.append(_err(
                f"{p.id} metric {n}: do not use % as the unit. "
                "Measure a duration, a count, a rate per 1,000 or money."
            ))
        issues += _check_metric(p.id, n, bullet, metric)
    if len({m.unit.strip().lower() for m in p.metrics}) < 2:
        issues.append(_warn(f"{p.id}: all metrics use the same unit. Mix time, quality, cost or throughput."))
    round_count = sum(1 for m in p.metrics if _is_round(m.baseline) and _is_round(m.result))
    if round_count >= 2:
        issues.append(_err(
            f"{p.id}: {round_count} of 3 metrics use round figures (like 500 to 150). "
            "Use natural-looking values such as 18, 47, 1.8 or 240."
        ))
    return issues


def _check_academic(p: ReferenceProject) -> list[Issue]:
    issues: list[Issue] = []
    if p.metrics:
        issues.append(_err(f"{p.id}: an academic project must not have business metrics."))
    if not (p.readiness_statement and p.readiness_statement.strip()):
        issues.append(_err(f"{p.id}: an academic project needs a readiness_statement."))

    text = " ".join(p.cv_bullets + [p.readiness_statement or "", p.scenario])
    if _MONEY_OR_PERCENT.search(text):
        issues.append(_err(f"{p.id}: an academic project must not contain percentages or money."))
    found = sorted(set(re.findall(r"[a-z]+", text.lower())) & _BUSINESS_WORDS)
    if found:
        issues.append(_err(f"{p.id}: academic wording claims business results: {found}"))
    return issues


_META_WORDS = {
    "figure", "figures", "natural-looking", "employer", "achievement", "achievements",
    "placeholder", "placeholders",
}


MAX_PROBLEM_CHARS = 260  # the "Problem tackled" line on the one-page CV
MAX_HOW_BUILT_CHARS = 170  # the "How it was built" line on the one-page CV


def check_project(p: ReferenceProject) -> list[Issue]:
    issues: list[Issue] = []
    for rid in p.covers_requirement_ids:
        if not _REQ_ID.match(rid):
            issues.append(_err(f"{p.id}: '{rid}' is not a valid requirement ID."))
    for n, bullet in enumerate(p.cv_bullets, start=1):
        words = len(bullet.split())
        if words > MAX_BULLET_WORDS:
            issues.append(_err(f"{p.id} bullet {n} has {words} words (maximum {MAX_BULLET_WORDS})."))

    # Warnings only: the employer can shorten the text in the preview before downloading.
    if len(p.scenario) > MAX_PROBLEM_CHARS:
        issues.append(_warn(
            f"{p.id}: the problem line has {len(p.scenario)} characters (aim for {MAX_PROBLEM_CHARS} or fewer "
            "so the CV stays on one page)."
        ))
    if len(p.architecture) > MAX_HOW_BUILT_CHARS:
        issues.append(_warn(
            f"{p.id}: the 'how it was built' line has {len(p.architecture)} characters (aim for "
            f"{MAX_HOW_BUILT_CHARS} or fewer so the CV stays on one page)."
        ))

    leaked = sorted(set(re.findall(r"[a-z\-]+", " ".join(p.constraints).lower())) & _META_WORDS)
    if leaked:
        issues.append(_err(
            f"{p.id}: constraints must describe the situation (data size, deadline, compliance), "
            f"not writing instructions. Remove: {leaked}"
        ))

    issues += _check_work(p) if p.kind == "work" else _check_academic(p)
    return issues




_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
_GENERIC = {
    "the", "and", "for", "with", "from", "that", "this", "are", "you", "our", "your",
    "experience", "years", "year", "hands", "hands-on", "building", "build", "knowledge",
    "solid", "strong", "good", "great", "ability", "skills", "skill", "working", "work",
    "using", "exposure", "familiarity", "proficiency", "understanding", "plus", "preferred",
    "required", "least", "minimum", "of", "or", "to", "in", "on", "at", "an", "as", "is",
    "be", "by", "a", "have", "has", "some", "basic", "advanced", "level", "related",
    "similar", "including", "etc", "use",
}


def _words(text: str) -> set[str]:
    """Distinctive lowercase words (tool names, topics), without filler or bare numbers."""
    found: set[str] = set()
    for word in _TOKEN.findall(text.lower()):
        word = word.rstrip(".-")
        if len(word) >= 2 and word not in _GENERIC and not word.strip("+").isdigit():
            found.add(word)
    return found


def check_project_set(projects: list[ReferenceProject], requirements: list[Requirement]) -> list[Issue]:
    """Checks across all three projects: structure and requirement coverage."""
    issues: list[Issue] = []

    if [p.kind for p in projects] != ["work", "work", "academic"]:
        issues.append(_err("The set must be exactly: work, work, academic (in that order)."))
    if [p.id for p in projects] != ["P1", "P2", "P3"]:
        issues.append(_err("Project IDs must be P1, P2, P3 in order."))

    by_id = {r.id: r for r in requirements}
    covered: set[str] = set()

    for p in projects:
        if len(p.covers_requirement_ids) < 2:
            issues.append(_err(f"{p.id} should cover at least 2 requirements."))

        project_text = " ".join(
            [p.title, p.scenario, p.architecture, " ".join(p.stack),
             " ".join(p.cv_bullets), " ".join(p.evidence_signals)]
        )
        project_words = _words(project_text)

        for rid in p.covers_requirement_ids:
            req = by_id.get(rid)
            if req is None:
                issues.append(_err(f"{p.id} claims {rid}, which is not in the requirement list."))
                continue
            terms = _words(req.text)
            if not req.is_ambiguous and terms and not (terms & project_words):
                issues.append(
                    _err(f"{p.id} claims {rid} ('{req.text}') but never mentions its key terms.")
                )
                continue
            covered.add(rid)

    for req in requirements:
        if req.importance == "mandatory" and not req.is_ambiguous and req.id not in covered:
            issues.append(_err(f"Mandatory requirement {req.id} ('{req.text}') is not covered by any project."))

    return issues





def _project_words(p: ReferenceProject) -> set[str]:
    return _words(
        " ".join([p.title, p.scenario, p.architecture, " ".join(p.stack),
                  " ".join(p.cv_bullets), " ".join(p.evidence_signals)])
    )


def check_claims(p: ReferenceProject, requirements: list[Requirement], targets: list[str]) -> list[Issue]:
    """Does this one project really cover what it claims, and what it was assigned?"""
    by_id = {r.id: r for r in requirements}
    project_words = _project_words(p)
    issues: list[Issue] = []
    proven: set[str] = set()

    for rid in p.covers_requirement_ids:
        req = by_id.get(rid)
        if req is None:
            issues.append(_err(f"{p.id} claims {rid}, which is not in the requirement list."))
            continue
        terms = _words(req.text)
        if not req.is_ambiguous and terms and not (terms & project_words):
            issues.append(
                _err(f"{p.id} claims {rid} ('{req.text}') but its stack, bullets and evidence signals never mention the key terms.")
            )
            continue
        proven.add(rid)

    for rid in targets:
        if rid not in proven:
            text = by_id[rid].text if rid in by_id else ""
            issues.append(
                _err(f"{p.id} must cover {rid} ('{text}'): list it in covers_requirement_ids and mention its key terms.")
            )
    return issues




def _is_round(value: float) -> bool:
    """True for whole numbers that are multiples of 5, such as 5, 30, 150, 500."""
    return float(value).is_integer() and value >= 5 and value % 5 == 0


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _similarity(a: str, b: str) -> float:
    """0 to 1: how many words two texts share (Jaccard similarity)."""
    wa, wb = _word_set(a), _word_set(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def check_against_previous(p: ReferenceProject, previous: list[ReferenceProject]) -> list[Issue]:
    """Each project must be clearly different from the ones written before it."""
    issues: list[Issue] = []
    for q in previous:
        if _similarity(p.title, q.title) >= 0.6:
            issues.append(_err(f"{p.id}'s title is almost the same as {q.id}'s. Choose a different project."))
        if _similarity(p.scenario, q.scenario) >= 0.5:
            issues.append(_err(f"{p.id}'s scenario repeats {q.id}'s. Use a completely different situation."))
        for n, bullet in enumerate(p.cv_bullets, start=1):
            for m, other in enumerate(q.cv_bullets, start=1):
                if _similarity(bullet, other) >= 0.6:
                    issues.append(_err(
                        f"{p.id} bullet {n} is nearly identical to {q.id} bullet {m}. Write a different achievement."
                    ))
        old_pairs = {(m.baseline, m.result) for m in q.metrics}
        for metric in p.metrics:
            if (metric.baseline, metric.result) in old_pairs:
                issues.append(_err(
                    f"{p.id} reuses {q.id}'s figures ({_fmt(metric.baseline)} to {_fmt(metric.result)}). Use different numbers."
                ))
    return issues