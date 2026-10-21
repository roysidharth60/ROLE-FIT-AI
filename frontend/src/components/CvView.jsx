import Checklist from "./Checklist";

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

function renderProject(p) {
  return (
    <div key={p.id} style={{ marginBottom: "10px" }}>
      <div style={{ fontWeight: "bold" }}>{p.title}</div>
      <div style={{ fontStyle: "italic", fontSize: "0.85rem", color: "#555" }}>{p.label}</div>
      <ul style={{ margin: "4px 0 0 18px" }}>
        {p.cv_bullets.map((b, i) => (
          <li key={i}>{b}</li>
        ))}
      </ul>
    </div>
  );
}

export default function CvView({ cv }) {
  const work = cv.projects.filter((p) => p.kind === "work");
  const academic = cv.projects.filter((p) => p.kind !== "work");
  return (
    <div>
      <div style={paper}>
        <div style={{ fontSize: "1.3rem", fontWeight: "bold" }}>{cv.candidate_name}</div>
        <div style={{ color: "#555" }}>{cv.contact_line}</div>
        <div style={{ fontSize: "1.1rem", marginTop: "6px" }}>{cv.target_title}</div>

        <h4 style={heading}>PROFESSIONAL SUMMARY</h4>
        <p style={{ margin: 0 }}>{cv.summary}</p>

        <h4 style={heading}>SKILLS</h4>
        {cv.skill_groups.map((g) => (
          <div key={g.label}>
            <strong>{g.label}: </strong>
            {g.items.join(", ")}
          </div>
        ))}

        <h4 style={heading}>PROJECT EXPERIENCE</h4>
        {work.map(renderProject)}

        {academic.length > 0 && <h4 style={heading}>ACADEMIC PROJECT</h4>}
        {academic.map(renderProject)}

        <h4 style={heading}>EDUCATION</h4>
        <p style={{ margin: 0, color: "#555" }}>{cv.education_note}</p>

        <p style={{ marginTop: "16px", fontStyle: "italic", fontSize: "0.85rem", color: "#555" }}>{cv.label}</p>
      </div>
      <Checklist items={cv.checklist} />
    </div>
  );
}