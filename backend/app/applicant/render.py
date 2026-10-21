"""Fill the candidate's TEMPLATE .docx with chosen text. No AI.

Input : the template file + a "mapping" (what text goes into which slot).
Output: a new .docx that keeps the template's page setup, fonts, colours and
        divider line, but contains only the mapped text.

mapping = {
    "values":       {"t4.text": "My summary", "tsec3.title": "PROJECT EXPERIENCE", ...},
    "extra_items":  {"t22": 2},        # 2 extra copies of item t22 (e.g. more bullets)
    "extra_groups": {"tsec3g1": 1},    # 1 extra copy of a whole entry
}

Slot ids come from the analyzer (item id + "." + field name). Copies get a suffix:
    extra item copy  ->  "t22+1", "t22+2"       (fields: "t22+1.text")
    extra entry copy ->  "t11@1"                (fields: "t11@1.part1"; its own extra
                                                 bullets are "t15@1+1" ...)
Rules: an empty slot means "nothing there"; a paragraph with no text is left out.
"""
import copy

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .analyzer import _number
from .docx_reader import parse_docx


# ---------- tiny XML helpers ----------

def _runs_with_text(p_el):
    """[(run element, inside_hyperlink)] for runs that contain text."""
    found = []
    for run in p_el.iter(qn("w:r")):
        if any(a.tag == qn("w:txbxContent") for a in run.iterancestors()):
            continue
        text = "".join((c.text or "") for c in run if c.tag == qn("w:t"))
        if text.strip():
            in_link = any(a.tag == qn("w:hyperlink") for a in run.iterancestors())
            found.append((run, in_link))
    return found


def _is_bold(rpr):
    if rpr is None:
        return False
    b = rpr.find(qn("w:b"))
    return b is not None and b.get(qn("w:val")) not in ("0", "false", "off")


def _clean_rpr(run):
    """Copy of a run's character formatting, without the PDF-conversion letter spacing."""
    rpr = run.find(qn("w:rPr")) if run is not None else None
    new = copy.deepcopy(rpr) if rpr is not None else OxmlElement("w:rPr")
    for tag in ("w:spacing",):
        for el in new.findall(qn(tag)):
            new.remove(el)
    return new


def _plain_rpr(rpr):
    """Same formatting but not bold (used when a template line has no plain run)."""
    new = copy.deepcopy(rpr)
    for tag in ("w:b", "w:bCs"):
        for el in new.findall(qn(tag)):
            new.remove(el)
    return new


class RunStyles:
    """Character formatting taken from one template paragraph."""

    def __init__(self, p_el):
        runs = _runs_with_text(p_el)
        usable = [r for r, linked in runs if not linked] or [r for r, _ in runs]
        first = usable[0] if usable else None
        self.main = _clean_rpr(first)
        bold = next((r for r in usable if _is_bold(r.find(qn("w:rPr")))), None)
        plain = next((r for r in usable if not _is_bold(r.find(qn("w:rPr")))), None)
        self.label = _clean_rpr(bold) if bold is not None else self.main
        self.value = _clean_rpr(plain) if plain is not None else _plain_rpr(self.main)


def _ppr(p_el):
    return p_el.find(qn("w:pPr"))


def _make_paragraph(ppr, runs):
    """New <w:p> with the given paragraph properties and [(text, rPr)] runs."""
    p = OxmlElement("w:p")
    if ppr is not None:
        p.append(copy.deepcopy(ppr))
    for text, rpr in runs:
        r = OxmlElement("w:r")
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
        p.append(r)
    return p


def _clean_text(value):
    return " ".join(str(value or "").split())


# ---------- spacing patterns (B6: copy the look of a template paragraph with the same role) ----------

class SpacingPatterns:
    """Template paragraphs are spaced unevenly (PDF conversion). To get an even,
    professional result we reuse ONE good example paragraph per role: its spacing
    and its fonts both come from that same paragraph."""

    def __init__(self, parsed, pristine):
        self.first_bullet = self.later_bullet = self.labeled = None
        self.doc_later_title = None
        self.section_titles = {}            # section id -> (first, later)
        # every heading after the first one reuses the second heading's spacing
        self.later_heading = (pristine[parsed["sections"][1]["para"]]
                              if len(parsed["sections"]) > 1 else None)
        for sec in parsed["sections"]:
            titles = []
            for grp in sec["groups"]:
                seen = 0
                for it in grp["items"]:
                    ppr = pristine[it["paras"][0]]       # the whole example paragraph
                    if it["role"] == "bullet":
                        seen += 1
                        if seen == 1 and self.first_bullet is None:
                            self.first_bullet = ppr
                        if seen >= 2 and self.later_bullet is None:
                            self.later_bullet = ppr
                    elif it["role"] == "labeled" and self.labeled is None:
                        self.labeled = ppr
                    elif it["role"] == "entry_title":
                        titles.append(ppr)
            if len(titles) >= 2 and self.doc_later_title is None:
                self.doc_later_title = titles[1]
            self.section_titles[sec["id"]] = titles
        self.later_bullet = self.later_bullet if self.later_bullet is not None else self.first_bullet

    def title(self, sec_id, rank):
        """rank 0 = first entry shown in the section, otherwise a later entry."""
        titles = self.section_titles.get(sec_id) or []
        if not titles:
            return None
        if rank == 0:
            return titles[0]
        if len(titles) >= 2:
            return titles[1]
        return self.doc_later_title if self.doc_later_title is not None else titles[0]


# ---------- turning one item into runs ----------

def _compose(item, inst_id, values, styles):
    """Return [(text, rPr)] for the item, or [] when its slots are empty."""
    def v(name):
        return _clean_text(values.get(f"{inst_id}.{name}", ""))

    role = item["role"]
    names = [f["name"] for f in item["fields"]]
    if role in ("name", "tagline", "text", "bullet"):
        text = v("text")
        return [(text, styles.main)] if text else []
    if role in ("contact", "entry_title", "subline"):
        text = " | ".join(t for t in (v(n) for n in names) if t)
        return [(text, styles.main)] if text else []
    if role in ("tech", "duration", "repo"):
        label, value = v("label"), v("value")
        if not value:
            return []
        text = f"{label.rstrip(':')}: {value}" if label else value
        return [(text, styles.main)]
    if role == "labeled":
        label, value = v("label"), v("value")
        if not value:
            return []
        if not label:
            return [(value, styles.value)]
        return [(label.rstrip(":") + ":", styles.label), (" " + value, styles.value)]
    return []


def _extra_line_paragraphs(lines, grp, pristine, patterns):
    """Paragraphs for the lines that sit above an entry's bullets (label bold, text plain)."""
    source = patterns.labeled
    if source is None:
        for it in grp["items"]:
            if it["role"] in ("tech", "text", "subline", "duration"):
                source = pristine[it["paras"][0]]
                break
    if source is None:
        source = pristine[grp["items"][0]["paras"][0]]
    styles = RunStyles(source)
    out = []
    for line in lines:
        label = _clean_text(line.get("label", "")).rstrip(":")
        value = _clean_text(line.get("value", ""))
        if not value:
            continue
        runs = [(label + ":", styles.label), (" " + value, styles.value)] if label else [(value, styles.value)]
        out.append(_make_paragraph(_ppr(source), runs))
    return out


# ---------- the main function ----------

def render_docx(template_path, mapping, out_path):
    values = (mapping or {}).get("values") or {}
    extra_items = (mapping or {}).get("extra_items") or {}
    extra_groups = (mapping or {}).get("extra_groups") or {}
    extra_lines = (mapping or {}).get("extra_lines") or {}

    doc = Document(str(template_path))
    body = list(doc.paragraphs)
    pristine = {i: copy.deepcopy(p._p) for i, p in enumerate(body)}
    parsed = _number(parse_docx(template_path), "t")
    patterns = SpacingPatterns(parsed, pristine)

    def style_of(item):
        return RunStyles(pristine[item["paras"][0]])

    def replace_paragraphs(item, new_elements):
        """Header items: put new paragraph(s) where the old one was."""
        anchor = body[item["paras"][0]]._p
        for el in new_elements:
            anchor.addprevious(el)
        anchor.getparent().remove(anchor)

    # ----- header: name, job title, contact -----
    head_items = [parsed["name"]] + parsed["tagline"] + ([parsed["contact"]] if parsed["contact"] else [])
    for item in head_items:
        runs = _compose(item, item["id"], values, style_of(item))
        new = [_make_paragraph(_ppr(pristine[item["paras"][0]]), runs)] if runs else []
        replace_paragraphs(item, new)

    # ----- sections -----
    headings_shown = 0
    for sec in parsed["sections"]:
        out = []
        heading_el = body[sec["para"]]._p
        title = _clean_text(values.get(f"{sec['id']}.title", ""))
        if title:
            source = pristine[sec["para"]]
            if headings_shown > 0 and patterns.later_heading is not None:
                source = patterns.later_heading
            headings_shown += 1
            out.append(_make_paragraph(_ppr(source), [(title, RunStyles(source).main)]))

        shown_entries = 0
        for grp in sec["groups"]:
            for clone in range(0, 1 + int(extra_groups.get(grp["id"], 0))):
                suffix = f"@{clone}" if clone else ""
                chunk = []
                for item in grp["items"]:
                    base = item["id"] + suffix
                    chunk.append((base, item))
                    for k in range(1, int(extra_items.get(base, 0)) + 1):
                        chunk.append((f"{base}+{k}", item))

                chunk_els, bullets_shown = [], 0
                lines = extra_lines.get(grp["id"] + suffix) or []
                lines_done = not lines
                for inst_id, item in chunk:
                    role = item["role"]
                    if role == "bullet" and not lines_done:
                        chunk_els += _extra_line_paragraphs(lines, grp, pristine, patterns)
                        lines_done = True
                    source = pristine[item["paras"][0]]          # default: the item's own paragraph
                    if role == "bullet":
                        patt = patterns.first_bullet if bullets_shown == 0 else patterns.later_bullet
                        source = patt if patt is not None else source
                    elif role == "labeled" and patterns.labeled is not None:
                        source = patterns.labeled
                    elif role == "entry_title":
                        patt = patterns.title(sec["id"], shown_entries)
                        source = patt if patt is not None else source
                    runs = _compose(item, inst_id, values, RunStyles(source))
                    if not runs:
                        continue
                    if role == "bullet":
                        bullets_shown += 1
                    chunk_els.append(_make_paragraph(_ppr(source), runs))
                if not lines_done:                      # an entry without bullets
                    chunk_els += _extra_line_paragraphs(lines, grp, pristine, patterns)
                if chunk_els:
                    shown_entries += 1
                    out += chunk_els

        # swap old section paragraphs for the new ones
        for el in out:
            heading_el.addprevious(el)
        old = {sec["para"]}
        for grp in sec["groups"]:
            for item in grp["items"]:
                old.update(item["paras"])
        for idx in old:
            node = body[idx]._p
            if node.getparent() is not None:
                node.getparent().remove(node)

    doc.save(str(out_path))
    return out_path