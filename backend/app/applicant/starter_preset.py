"""The "starter preset": your hand-made mapping (handoff section B7) as a rule-based builder.

It fills the template slots from the two analysed documents so you can test the
renderer before drag and drop exists. Later it becomes the
"Start from suggested mapping" button.

B7 rules in short
  header      name + contact from the TEMPLATE, job title from the INFO
  headings    template wording, except the work heading which comes from the INFO (UPPERCASE)
  summary     from the INFO
  skills      the INFO's skill lines replace the template's skill lines
  work        the INFO's entries, title = "<job title> | <entry title>", tech line without label.
              No company name and no dates are written for these entries: they are
              illustrative reference projects, not real employment.
              Above the bullets each entry gets the lines the reference CV carries:
              the "Illustrative ..." label, "Problem tackled" and "How it was built".
  projects    the INFO's academic project first, then ONLY the template's first project
  education / certifications   copied from the TEMPLATE unchanged
"""

PRESET_REPOSITORY = "github.com/roysidharth60/Project"   # given in B7 for the academic project


def _text(item, name):
    for f in item["fields"]:
        if f["name"] == name:
            return f["text"]
    return ""


def _fid(item, name):
    for f in item["fields"]:
        if f["name"] == name:
            return f["id"]
    return None


def build_starter(analysis):
    tmpl = analysis["template"]
    info = analysis["sources"]["info"]
    own = analysis["sources"]["template"]          # the template's own content
    values, extra_items, extra_groups, extra_lines = {}, {}, {}, {}

    def put(item, name, text, suffix=""):
        fid = _fid(item, name)
        if fid and text is not None:
            key = fid if not suffix else fid.replace(".", suffix + ".", 1)
            values[key] = text

    def copy_by_position(t_sec, o_sec):
        """Template section content copied as-is (same file, so same shape)."""
        for tg, og in zip(t_sec["groups"], o_sec["groups"]):
            for ti, oi in zip(tg["items"], og["items"]):
                for tf, of in zip(ti["fields"], oi["fields"]):
                    values[tf["id"]] = of["text"]
                    # If fields are missing in one but not the other (e.g., no company name in info), use template's
                    if tf["id"] not in [f["id"] for f in oi["fields"]]:
                        values[tf["id"]] = tf["text"]

    def items_of(group, role):
        return [i for i in group["items"] if i["role"] == role]

    def put_bullets(t_items, bullets, suffix):
        """Fill bullet slots; ask for extra copies when there are more bullets than slots."""
        for t_item, b in zip(t_items, bullets):
            put(t_item, "text", _text(b, "text"), suffix)
        if len(bullets) > len(t_items) and t_items:
            base = t_items[-1]["id"] + suffix
            extra_items[base] = len(bullets) - len(t_items)
            for k, b in enumerate(bullets[len(t_items):], start=1):
                values[f"{base}+{k}.text"] = _text(b, "text")   # text of the extra copy

    def fill_entry(tg, ig, suffix, position, is_work, first_entry):
        title_item = (items_of(tg, "entry_title") or [None])[0]
        info_title = (items_of(ig, "entry_title") or [None])[0]
        if title_item and info_title:
            name = _text(info_title, "part1")
            if is_work and position:
                put(title_item, "part1", position, suffix)
                put(title_item, "part2", name, suffix)
            else:
                put(title_item, "part1", name, suffix)
            tech = _text(info_title, "part2")
            for t_item in items_of(tg, "tech")[:1]:
                put(t_item, "label", "", suffix)
                put(t_item, "value", tech, suffix)
        # Lines above the bullets, copied from the reference entry: the "Illustrative ..." label,
        # "Problem tackled" / "Question explored" and "How it was built".
        lines = []
        for it in ig["items"]:
            if it["role"] == "bullet":
                break
            if it["role"] == "subline":
                subline_text = " | ".join(f["text"] for f in it["fields"])
                lower_text = subline_text.lower()
                if "illustrative academic reference project" in lower_text:
                    subline_text = "CDAC PROJECTS"
                elif (
                    "CDAC PROJECTS" 
                    
                ):
                    subline_text = (
                        ""
                    )
                lines.append({"label": "", "value": subline_text})
            if it["role"] == "subline":
                subline_text = " | ".join(f["text"] for f in it["fields"])
                if (
                    "illustrative reference project" in subline_text.lower()
                    and "all figures are examples" in subline_text.lower()
                ):
                    subline_text = "INTAGLIO SOLUTIONS PVT LTD DEC 2024 - FEB 2025"
                lines.append({"label": "", "value": subline_text})
            elif it["role"] == "labeled":
                lines.append({"label": _text(it, "label"), "value": _text(it, "value")})
        if lines:
            extra_lines[tg["id"] + suffix] = lines
        put_bullets(items_of(tg, "bullet"), items_of(ig, "bullet"), suffix)
        if not is_work:
            for t_item in items_of(tg, "repo")[:1]:
                put(t_item, "label", "Repository", suffix)
                put(t_item, "value", PRESET_REPOSITORY, suffix)

    # map template group -> same group in the template's own content (same file, same order)
    own_group_for = {}
    for t_sec, o_sec in zip(tmpl["sections"], own["sections"]):
        for tg, og in zip(t_sec["groups"], o_sec["groups"]):
            own_group_for[tg["id"]] = og

    # ----- header -----
    values[_fid(tmpl["name"], "text")] = _text(own["name"], "text")
    position = _text(info["tagline"][0], "text") if info["tagline"] else ""
    for t_item, o_item in zip(tmpl["tagline"], own["tagline"]):
        values[_fid(t_item, "text")] = position or _text(o_item, "text")
    if tmpl["contact"] and own["contact"]:
        for f in tmpl["contact"]["fields"]:
            values[f["id"]] = _text(own["contact"], f["name"])

    # ----- sections -----
    for t_sec, o_sec in zip(tmpl["sections"], own["sections"]):
        canon = t_sec["canonical"]
        values[f"{t_sec['id']}.title"] = t_sec["title"]
        info_secs = [s for s in info["sections"] if s["suggested_target"] == t_sec["id"]]

        if canon in ("education", "certifications") or not info_secs:
            copy_by_position(t_sec, o_sec)
            continue

        if canon == "summary":
            for t_item, i_item in zip(t_sec["groups"][0]["items"], info_secs[0]["groups"][0]["items"]):
                put(t_item, "text", _text(i_item, "text"))

        elif canon == "skills":
            t_items = t_sec["groups"][0]["items"]
            i_items = [i for g in info_secs[0]["groups"] for i in g["items"] if i["role"] == "labeled"]
            for t_item, i_item in zip(t_items, i_items):
                put(t_item, "label", _text(i_item, "label"))
                put(t_item, "value", _text(i_item, "value"))
            if len(i_items) > len(t_items):
                base = t_items[-1]["id"]
                extra_items[base] = len(i_items) - len(t_items)
                for k, i_item in enumerate(i_items[len(t_items):], start=1):
                    values[f"{base}+{k}.label"] = _text(i_item, "label")
                    values[f"{base}+{k}.value"] = _text(i_item, "value")

        elif canon == "work":
            if info_secs[0]["canonical"] == "work":
                values[f"{t_sec['id']}.title"] = "WORK EXPERIENCE"
            i_groups = [g for s in info_secs for g in s["groups"] if g["kind"] == "entry"]
            t_groups = t_sec["groups"]
            for n, ig in enumerate(i_groups):
                if n < len(t_groups):
                    fill_entry(t_groups[n], ig, "", position, True, n == 0)
                else:
                    clone = n - len(t_groups) + 1
                    src = t_groups[-1]
                    extra_groups[src["id"]] = clone
                    fill_entry(src, ig, f"@{clone}", position, True, False)

        elif canon == "projects":
            values[f"{t_sec['id']}.title"] = "ACADEMIC PROJECTS"
            i_groups = [g for s in info_secs for g in s["groups"] if g["kind"] == "entry"]
            i_groups = [g for s in info_secs for g in s["groups"] if g["kind"] == "entry"]
            t_groups = t_sec["groups"]
            for tg, ig in zip(t_groups, i_groups):
                fill_entry(tg, ig, "", position, False, False)
            # then only the template's own FIRST project (B7: ServiConnect)
            slot = len(i_groups)
            if slot < len(t_groups) and o_sec["groups"]:
                tg, og = t_groups[slot], o_sec["groups"][0]
                for ti, oi in zip(tg["items"], og["items"]):
                    for tf, of in zip(ti["fields"], oi["fields"]):
                        values[tf["id"]] = of["text"]
        else:
            copy_by_position(t_sec, o_sec)

    return {"values": values, "extra_items": extra_items, "extra_groups": extra_groups,
            "extra_lines": extra_lines}