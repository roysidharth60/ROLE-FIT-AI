import re
from app.models import Metric, MetricPlan, WorkBulletPlan

PLACEHOLDERS = ("{baseline}", "{result}", "{pct}")


def fmt(value: float) -> str:
    """90.0 -> '90', 0.24 -> '0.24', 1.8 -> '1.8'"""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _natural(value: float, nudge: int) -> float:
    """Make a figure look measured, not chosen: avoid whole multiples of 5."""
    if value >= 5:
        v = round(value)
        if v % 5 == 0:
            v += nudge
        return float(v)
    if value >= 1:
        return round(value, 1)
    return round(value, 2)


def _finalize_metric(plan: MetricPlan, index: int) -> Metric:
    nudge = (1, -1, 2, -2)[index % 4]
    baseline = _natural(plan.baseline_hint, nudge)
    if plan.direction == "decrease":
        factor = 1 - plan.improvement_pct / 100
    else:
        factor = 1 + plan.improvement_pct / 100
    result = _natural(baseline * factor, -nudge)

    # Safety nets so the direction always holds
    if plan.direction == "decrease" and not result < baseline:
        result = baseline - 1 if baseline > 2 else round(baseline * 0.8, 2)
    if plan.direction == "increase" and not result > baseline:
        result = baseline + 1
    if result <= 0:
        result = round(baseline * 0.5, 2)

    return Metric(
        name=plan.name,
        unit=plan.unit,
        baseline=baseline,
        result=result,
        direction=plan.direction,
    )

def with_unit(value: float, unit: str) -> str:
    """121, 'minutes' -> '121 minutes'. A value of 1 gets the singular form."""
    unit = unit.strip()
    if value == 1 and unit.lower().endswith("s"):
        unit = unit[:-1]
    return f"{fmt(value)} {unit}"


_UNIT_WORDS = r"(?:hours?|minutes?|seconds?|days?|weeks?|months?|errors?|bugs?|tickets?|%|percent)"



def finalize_work_bullets(bullets: list[WorkBulletPlan]) -> tuple[list[str], list[Metric]]:
    """Turn the model's placeholder bullets into final text and exact metrics."""
    texts: list[str] = []
    metrics: list[Metric] = []
    for i, bullet in enumerate(bullets):
        missing = [p for p in PLACEHOLDERS if p not in bullet.text]
        if missing:
            raise ValueError(
                f"Bullet {i + 1} must contain the placeholders {', '.join(PLACEHOLDERS)} "
                f"(missing {', '.join(missing)}). Do not write the numbers yourself."
            )
        unit = bullet.metric.unit.strip()
        if unit.lower() in {"%", "percent", "percentage", "count", "number", "value", "rating", "ratings", "score", "scores", "points", "stars"} or "satisfaction" in bullet.metric.name.lower():
            raise ValueError(
                f"Bullet {i + 1}: the unit must be a plural noun such as minutes, hours, errors, tickets, "
                f"or dollars. Not '{unit}'."
            )
        if re.search(r"\{(?:baseline|result)\}\s*" + _UNIT_WORDS, bullet.text, re.IGNORECASE):
            raise ValueError(
                f"Bullet {i + 1}: never write a unit after {{baseline}} or {{result}}. "
                f"The program adds it. Write 'from {{baseline}} to {{result}} ({{pct}}%)'."
            )

        metric = _finalize_metric(bullet.metric, i)
        pct = round(abs(metric.result - metric.baseline) / metric.baseline * 100)
        text = bullet.text.replace(
            "{baseline} to {result}", f"{fmt(metric.baseline)} to {with_unit(metric.result, unit)}"
        )
        text = (
            text.replace("{baseline}", with_unit(metric.baseline, unit))
            .replace("{result}", with_unit(metric.result, unit))
            .replace("{pct}", str(pct))
        )
        texts.append(text)
        metrics.append(metric)
    return texts, metrics