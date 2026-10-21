import re
from io import BytesIO

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.models import ChecklistItem, ReferenceCV, ReferenceProject

FONT = "Calibri"
STANDARD_HEADINGS = ["Professional Summary", "Skills", "Project Experience", "Academic Project", "Education"]
REQUIRED_HEADINGS = ["Professional Summary", "Skills", "Project Experience"]


def _style_document(doc: Document) -> None:
    section = doc.sections[0]
    section.left_margin = section.right_margin = Inches(0.7)
    section.top_margin = section.bottom_margin = Inches(0.5)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.space_after = Pt(2)

    heading = doc.styles["Heading 1"]
    heading.font.name = FONT
    heading.font.size = Pt(11)
    heading.font.bold = True
    heading.font.color.rgb = RGBColor(0, 0, 0)
    heading.paragraph_format.space_before = Pt(5)
    heading.paragraph_format.space_after = Pt(3)
    # Word's default heading uses theme fonts that would override Calibri; remove those links
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        heading.element.rPr.rFonts.attrib.pop(qn(attr), None)

    doc.styles["List Bullet"].paragraph_format.space_after = Pt(1)


def _heading(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph(text, style="Heading 1")
    # A thin line under the heading: a paragraph border, not a table or a drawing
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "808080")):
        bottom.set(qn(key), value)
    borders.append(bottom)
    p_pr.append(borders)


def _labelled(doc: Document, label: str, text: str) -> None:
    """One short paragraph: a bold label, then the text. Used for the two lines above the bullets."""
    para = doc.add_paragraph()
    para.add_run(label + ": ").bold = True
    para.add_run(text)
    para.paragraph_format.space_after = Pt(1)
    para.paragraph_format.keep_with_next = True


def _project(doc: Document, project: ReferenceProject) -> None:
    title = doc.add_paragraph()
    title.add_run(project.title).bold = True
    title.add_run(" | " + ", ".join(project.stack))
    title.paragraph_format.space_before = Pt(4)
    title.paragraph_format.space_after = Pt(1)
    title.paragraph_format.keep_with_next = True

    label = doc.add_paragraph()
    run = label.add_run(project.label)
    run.italic = True
    run.font.size = Pt(9)
    label.paragraph_format.keep_with_next = True

    first_label = "Problem tackled" if project.kind == "work" else "Question explored"
    _labelled(doc, first_label, project.scenario)
    _labelled(doc, "How it was built", project.architecture)

    for bullet in project.cv_bullets:
        doc.add_paragraph(bullet, style="List Bullet")

    if project.readiness_statement:
        para = doc.add_paragraph()
        para.add_run("Readiness: ").bold = True
        para.add_run(project.readiness_statement)


def build_docx(cv: ReferenceCV) -> bytes:
    """Single column, standard headings, real bullet styles, no tables, no images, no text boxes."""
    doc = Document()
    _style_document(doc)
    doc.core_properties.title = "Illustrative reference CV"
    doc.core_properties.author = "RoleFit AI (illustrative example)"

    name = doc.add_paragraph()
    run = name.add_run(cv.candidate_name)
    run.bold = True
    run.font.size = Pt(18)
    name.paragraph_format.space_after = Pt(0)

    doc.add_paragraph(cv.contact_line)
    doc.add_paragraph().add_run(cv.target_title).bold = True

    _heading(doc, "Professional Summary")
    doc.add_paragraph(cv.summary)

    _heading(doc, "Skills")
    for group in cv.skill_groups:
        para = doc.add_paragraph()
        para.add_run(group.label + ": ").bold = True
        para.add_run(", ".join(group.items))

    work = [p for p in cv.projects if p.kind == "work"]
    academic = [p for p in cv.projects if p.kind == "academic"]

    _heading(doc, "Project Experience")
    for project in work:
        _project(doc, project)

    if academic:
        _heading(doc, "Academic Project")
        for project in academic:
            _project(doc, project)

    _heading(doc, "Education")
    doc.add_paragraph(cv.education_note)

    note = doc.add_paragraph()
    run = note.add_run(cv.label)
    run.italic = True
    run.font.size = Pt(8.5)
    note.paragraph_format.space_before = Pt(8)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def verify_docx(data: bytes, cv: ReferenceCV) -> list[ChecklistItem]:
    """Open the finished file again and check what is really inside it."""
    doc = Document(BytesIO(data))
    xml = doc.element.xml
    full_text = "\n".join(p.text for p in doc.paragraphs)
    bullets_expected = [b for p in cv.projects for b in p.cv_bullets]
    items: list[ChecklistItem] = []

    tables = len(doc.tables)
    items.append(ChecklistItem(
        id="single_column", label="Single column: the file contains no tables",
        passed=tables == 0, detail=f"{tables} tables found.",
    ))

    graphics = len(doc.inline_shapes) + sum(xml.count(tag) for tag in ("w:txbxContent", "w:drawing", "w:pict"))
    items.append(ChecklistItem(
        id="no_graphics", label="No images, icons or text boxes",
        passed=graphics == 0, detail=f"{graphics} graphic elements found.",
    ))

    headings = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
    standard = all(h in STANDARD_HEADINGS for h in headings) and all(h in headings for h in REQUIRED_HEADINGS)
    items.append(ChecklistItem(
        id="standard_headings", label="Standard section headings, set as real headings",
        passed=standard, detail="Headings: " + ", ".join(headings),
    ))

    bullet_count = sum(1 for p in doc.paragraphs if p.style.name == "List Bullet")
    items.append(ChecklistItem(
        id="real_bullets", label="Bullets are real list bullets, not typed symbols",
        passed=bullet_count == len(bullets_expected),
        detail=f"{bullet_count} list bullets for {len(bullets_expected)} expected.",
    ))

    missing = [b[:30] for b in bullets_expected if b not in full_text]
    
    for proj in cv.projects:
        if proj.scenario not in full_text:
            missing.append(f"{proj.id} problem line")
        if proj.architecture not in full_text:
            missing.append(f"{proj.id} how-it-was-built line")

    items.append(ChecklistItem(
        id="text_extractable", label="All text can be read back from the file",
        passed=not missing,
        detail="The summary, the two lines above each project, and every bullet were extracted." 
           if not missing else f"Not found: {missing}",
    ))

    years = re.findall(r"\b(?:19|20)\d{2}\b", full_text)
    items.append(ChecklistItem(
        id="consistent_dates", label="Dates are consistent",
        passed=not years,
        detail="No dates are used (illustrative projects have none)." if not years else f"Dates found: {years}",
    ))
    return items


def export_with_checks(cv: ReferenceCV) -> tuple[bytes, ReferenceCV]:
    """Build the file, verify it, and return both the bytes and the CV with the full checklist."""
    data = build_docx(cv)
    full = cv.model_copy(update={"checklist": list(cv.checklist) + verify_docx(data, cv)})
    return data, full