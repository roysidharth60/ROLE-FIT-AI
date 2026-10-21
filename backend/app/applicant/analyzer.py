"""Turn parsed documents into the JSON the frontend shows.

The TEMPLATE structure becomes the placeholders (slots).
The INFO structure (and the template's own content) become draggable chips.
Both use the same shape, so the frontend can reuse one renderer.
"""
from .docx_reader import parse_docx
from .headings import COMPATIBLE


def _number(parsed, prefix):
    """Give every section, group, item and field a stable id like t3.f1."""
    n = 0

    def tag(item):
        nonlocal n
        n += 1
        item["id"] = f"{prefix}{n}"
        for f in item["fields"]:
            f["id"] = f"{item['id']}.{f['name']}"
        return item

    tag(parsed["name"])
    parsed["tagline"] = [tag(t) for t in parsed["tagline"]]
    if parsed["contact"]:
        tag(parsed["contact"])
    for si, sec in enumerate(parsed["sections"], start=1):
        sec["id"] = f"{prefix}sec{si}"
        for gi, grp in enumerate(sec["groups"], start=1):
            grp["id"] = f"{sec['id']}g{gi}"
            grp["items"] = [tag(i) for i in grp["items"]]
    return parsed


def _suggest_target(info_section, template_sections):
    """Which template section probably receives this info section?"""
    wanted = [info_section["canonical"]] + COMPATIBLE.get(info_section["canonical"], [])
    for key in wanted:
        for ts in template_sections:
            if key and ts["canonical"] == key:
                return ts["id"]
    return None


def analyze(info_path, template_path):
    info = _number(parse_docx(info_path), "i")
    template = _number(parse_docx(template_path), "t")
    # the template's own content is also a source (name, contact, education ...)
    template_content = _number(parse_docx(template_path), "tc")

    warnings = []
    for label, doc in (("Info file", info), ("Template file", template)):
        warnings += [f"{label}: {w}" for w in doc["warnings"]]

    tmpl_keys = {s["canonical"] for s in template["sections"] if s["canonical"]}
    for sec in info["sections"]:
        sec["suggested_target"] = _suggest_target(sec, template["sections"])
        if sec["suggested_target"] is None:
            warnings.append(
                f"Info section '{sec['title']}' has no matching heading in the template. "
                "You can still drag its content into any placeholder.")
    for sec in template_content["sections"]:
        sec["suggested_target"] = next(
            (ts["id"] for ts in template["sections"] if ts["canonical"] == sec["canonical"]), None)

    for d in (info, template, template_content):
        d.pop("warnings")
    return {
        "template": template,          # placeholders
        "sources": {"info": info, "template": template_content},  # chips
        "warnings": warnings,
    }