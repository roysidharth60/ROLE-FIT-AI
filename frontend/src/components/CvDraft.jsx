import { useState, useEffect } from "react";
import Checklist from "./Checklist";
import { rewriteBullets } from "../api";

const paper = {
  background: "#fff",
  color: "#111",
  border: "1px solid #ccc",
  borderRadius: "6px",
  padding: "20px 24px",
  margin: "12px 0",
  fontFamily: "Calibri, Arial, sans-serif",
};
const heading = { borderBottom: "1px solid #333", margin: "16px 0 6px", fontSize: "0.95rem", letterSpacing: "0.05em" };
const field = { width: "100%", boxSizing: "border-box", font: "inherit", padding: "4px 6px", margin: "2px 0" };
const NOTE_PLACEHOLDER =
  "Your request for these bullets, e.g. Add that weekly report time dropped from 6 hours to 2 hours (about 67%), in a plain, direct style";

function lines(text) {
  return text.split("\n").map((s) => s.trim()).filter(Boolean);
}
function wordCount(text) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}
function sentenceCount(text) {
  return (text.match(/[.!?](?:\s|$)/g) || []).length;
}
function snapshot(profile, projects) {
  return JSON.stringify([
    profile.target_title,
    profile.summary,
    profile.skill_groups.map((g) => [g.label, g.items]),
    projects.map((p) => [p.title, p.cv_bullets]),
  ]);
}

export default function CvDraft({ profile, projects, cv, busy, onRecheck, employerName, onDirtyChange }) {
  const [title, setTitle] = useState(profile.target_title);
  const [summary, setSummary] = useState(profile.summary);
  const [groups, setGroups] = useState(
    profile.skill_groups.map((g) => ({ label: g.label, itemsText: g.items.join("\n") }))
  );
  const [edits, setEdits] = useState(() =>
    Object.fromEntries(projects.map((p) => [p.id, { title: p.title, bulletsText: p.cv_bullets.join("\n") }]))
  );
  // Per-project controls for "Rewrite bullets with my note"
  const [notes, setNotes] = useState({});
  const [counts, setCounts] = useState({});
  const [limits, setLimits] = useState({});
  const [working, setWorking] = useState(""); // id of the project being rewritten
  const [info, setInfo] = useState({}); // id -> { issues, error, usage }
  const [backups, setBackups] = useState({}); // id -> bullets text before the last rewrite

  const locked = busy || working !== "";
  const noteOf = (id) => notes[id] || "";
  const limitOf = (id) => limits[id] || 30;
  const countOf = (id) => counts[id] || Math.min(3, Math.max(2, lines(edits[id].bulletsText).length));

  const editedProfile = {
    target_title: title.trim(),
    summary: summary.trim(),
    skill_groups: groups.map((g) => ({ label: g.label.trim(), items: lines(g.itemsText) })),
  };
  const editedProjects = projects.map((p) => ({
    ...p,
    title: edits[p.id].title.trim(),
    cv_bullets: lines(edits[p.id].bulletsText),
  }));

  // Problems that would make the backend reject the edit (same limits as the models)
  const problems = [];
  if (editedProfile.target_title.length < 3 || editedProfile.target_title.length > 80)
    problems.push("The job title must be 3 to 80 characters.");
  if (editedProfile.summary.length < 40 || editedProfile.summary.length > 800)
    problems.push("The summary must be 40 to 800 characters.");
  editedProfile.skill_groups.forEach((g, i) => {
    if (g.label.length < 3 || g.label.length > 40) problems.push(`Skill group ${i + 1}: the label must be 3 to 40 characters.`);
    if (g.items.length < 2 || g.items.length > 8) problems.push(`Skill group ${i + 1}: use 2 to 8 items, one per line.`);
    g.items.forEach((item) => {
      if (item.length > 40) problems.push(`Skill item "${item.slice(0, 25)}..." is longer than 40 characters.`);
    });
  });
  editedProjects.forEach((p) => {
    if (p.title.length < 3 || p.title.length > 100) problems.push(`${p.id}: the title must be 3 to 100 characters.`);
    if (p.cv_bullets.length < 2 || p.cv_bullets.length > 3) problems.push(`${p.id}: use 2 or 3 bullets, one per line.`);
  });
  const longBullets = editedProjects.flatMap((p) =>
    p.cv_bullets.filter((b) => wordCount(b) > limitOf(p.id)).map(() => p.id)
  );

  const dirty = snapshot(editedProfile, editedProjects) !== snapshot(profile, projects);

  
  // Tell the page whether there are CV edits that have not been checked yet (blocks Save and Publish)
  useEffect(() => {
    if (onDirtyChange) onDirtyChange(dirty);
  }, [dirty]); // eslint-disable-line react-hooks/exhaustive-deps

  function updateGroup(i, patch) {
    setGroups((gs) => gs.map((g, k) => (k === i ? { ...g, ...patch } : g)));
  }
  function addGroup() {
    if (groups.length < 4) setGroups([...groups, { label: "New group", itemsText: "" }]);
  }
  function removeGroup(i) {
    if (groups.length > 2) setGroups(groups.filter((_, k) => k !== i));
  }
  function updateProject(id, patch) {
    setEdits((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  }

  async function rewrite(p) {
    const e = edits[p.id];
    setWorking(p.id);
    setInfo((s) => ({ ...s, [p.id]: {} }));
    try {
      const res = await rewriteBullets({
        projectId: p.id,
        kind: p.kind,
        title: e.title.trim(),
        scenario: p.scenario,
        stack: p.stack,
        currentBullets: lines(e.bulletsText),
        employerNote: noteOf(p.id).trim(),
        employerName: employerName || "",
        bulletCount: countOf(p.id),
        maxWords: limitOf(p.id),
      });
      setBackups((s) => ({ ...s, [p.id]: e.bulletsText }));
      updateProject(p.id, { bulletsText: res.bullets.join("\n") });
      setInfo((s) => ({ ...s, [p.id]: { issues: res.issues, usage: res.usage } }));
    } catch (err) {
      setInfo((s) => ({ ...s, [p.id]: { error: err.message } }));
    } finally {
      setWorking("");
    }
  }

  function undo(id) {
    updateProject(id, { bulletsText: backups[id] });
    setBackups((s) => {
      const next = { ...s };
      delete next[id];
      return next;
    });
    setInfo((s) => ({ ...s, [id]: {} }));
  }

  function renderProject(p) {
    const e = edits[p.id];
    const bulletLines = lines(e.bulletsText);
    const limit = limitOf(p.id);
    const result = info[p.id] || {};
    return (
      <div key={p.id} style={{ marginBottom: "16px" }}>
        <p style={{ margin: 0, fontStyle: "italic", fontSize: "0.85rem", color: "#555" }}>{p.label}</p>
        <input
          style={{ ...field, fontWeight: "bold" }}
          value={e.title}
          maxLength={100}
          onChange={(ev) => updateProject(p.id, { title: ev.target.value })}
          disabled={locked}
        />
        <textarea
          style={field}
          rows={4}
          value={e.bulletsText}
          onChange={(ev) => updateProject(p.id, { bulletsText: ev.target.value })}
          disabled={locked}
        />
        <span className="muted">
          One bullet per line (2 or 3). Words:{" "}
          {bulletLines.map((b, i) => (
            <span key={i} style={{ color: wordCount(b) > limit ? "#b45309" : undefined }}>
              {i > 0 && " | "}
              {wordCount(b)}
            </span>
          ))}{" "}
          (limit {limit}).
        </span>

        <div style={{ background: "#f6f8fa", border: "1px solid #ddd", borderRadius: "6px", padding: "8px", marginTop: "6px" }}>
          <strong style={{ fontSize: "0.9rem" }}>Rewrite these bullets with your own request</strong>
          <textarea
            style={field}
            rows={2}
            maxLength={300}
            value={noteOf(p.id)}
            onChange={(ev) => setNotes((s) => ({ ...s, [p.id]: ev.target.value }))}
            placeholder={p.kind === "work" ? NOTE_PLACEHOLDER : "Your request, e.g. Show interest in clinic scheduling data and SQL practice"}
            disabled={locked}
          />
          <div className="row">
            <label>
              Bullets:{" "}
              <select
                value={countOf(p.id)}
                onChange={(ev) => setCounts((s) => ({ ...s, [p.id]: Number(ev.target.value) }))}
                disabled={locked}
              >
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </label>
            <label>
              Max words per bullet:{" "}
              <select
                value={limit}
                onChange={(ev) => setLimits((s) => ({ ...s, [p.id]: Number(ev.target.value) }))}
                disabled={locked}
              >
                {[20, 25, 30, 35, 40, 45].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <button className="secondary" onClick={() => rewrite(p)} disabled={locked || noteOf(p.id).trim().length < 3}>
              {working === p.id ? "Rewriting..." : "Rewrite bullets"}
            </button>
            {backups[p.id] !== undefined && (
              <button className="secondary" onClick={() => undo(p.id)} disabled={locked}>
                Undo last rewrite
              </button>
            )}
          </div>
          {result.error && <div className="error-box">{result.error}</div>}
          {result.issues && result.issues.length > 0 && (
            <div className="notice-box">
              <strong>Things to review in these bullets</strong>
              <ul>
                {result.issues.map((n, i) => (
                  <li key={i}>
                    <span className={`badge ${n.severity}`}>{n.severity}</span> {n.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.usage && (
            <span className="muted">
              ({result.usage.input_tokens} tokens in, {result.usage.output_tokens} out)
            </span>
          )}
        </div>
      </div>
    );
  }

  const workProjects = projects.filter((p) => p.kind === "work");
  const academicProjects = projects.filter((p) => p.kind !== "work");

  return (
    <div>
      <p className="muted">
        This is your draft. Everything below is editable. The name, contact details and education are bracketed
        placeholders, and the example label line is added by the backend in the downloaded file. Figures you
        type or request are used exactly as written. They are not verified, and the CV still labels them as
        examples. The "Example figures" on the project cards above are not updated by your bullet edits.
      </p>

      <div style={paper}>
        <input
          style={{ ...field, fontSize: "1.2rem", fontWeight: "bold" }}
          value={title}
          maxLength={80}
          onChange={(e) => setTitle(e.target.value)}
          disabled={locked}
        />

        <h4 style={heading}>PROFESSIONAL SUMMARY</h4>
        <textarea
          style={field}
          rows={5}
          value={summary}
          maxLength={800}
          onChange={(e) => setSummary(e.target.value)}
          disabled={locked}
        />
        <span className="muted">
          {sentenceCount(summary)} sentences, {wordCount(summary)} words.
        </span>

        <h4 style={heading}>SKILLS</h4>
        {groups.map((g, i) => (
          <div key={i} style={{ marginBottom: "8px" }}>
            <input
              style={{ ...field, fontWeight: "bold" }}
              value={g.label}
              maxLength={40}
              onChange={(e) => updateGroup(i, { label: e.target.value })}
              disabled={locked}
            />
            <textarea
              style={field}
              rows={3}
              value={g.itemsText}
              onChange={(e) => updateGroup(i, { itemsText: e.target.value })}
              disabled={locked}
            />
            <span className="muted">One skill per line (2 to 8, up to 40 characters each). </span>
            {groups.length > 2 && (
              <button className="secondary" onClick={() => removeGroup(i)} disabled={locked}>
                Remove group
              </button>
            )}
          </div>
        ))}
        {groups.length < 4 && (
          <button className="secondary" onClick={addGroup} disabled={locked}>
            Add skill group
          </button>
        )}

        <h4 style={heading}>PROJECT EXPERIENCE</h4>
        {workProjects.map(renderProject)}

        {academicProjects.length > 0 && <h4 style={heading}>ACADEMIC PROJECT</h4>}
        {academicProjects.map(renderProject)}

        <h4 style={heading}>EDUCATION</h4>
        <p style={{ margin: 0, color: "#555" }}>[Degree, institution and year are placeholders in the file.]</p>
      </div>

      {problems.length > 0 && (
        <div className="notice-box">
          <strong>Fix these before updating</strong>
          <ul>
            {problems.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}
      {longBullets.length > 0 && (
        <p className="muted">
          Some bullets in {[...new Set(longBullets)].join(", ")} are over their word limit. Long bullets may push the
          CV past one page.
        </p>
      )}

      <div className="row">
        <button onClick={() => onRecheck(editedProfile, editedProjects)} disabled={locked || !dirty || problems.length > 0}>
          {busy ? "Working..." : "Update CV and re-run checks"}
        </button>
        {dirty ? (
          <span className="muted">You have edits that are not checked yet. The check results below are out of date.</span>
        ) : (
          <span className="muted">The checks below were run on this version.</span>
        )}
      </div>

       {cv ? (
        <div style={{ opacity: dirty ? 0.5 : 1 }}>
          <Checklist items={cv.checklist} />
          {dirty && <p className="muted">Out of date: click "Update CV and re-run checks".</p>}
        </div>
      ) : (
        <p className="muted">{busy ? "Building the CV and running the checks..." : "The checks have not run yet."}</p>
      )}
    </div>
  );
}