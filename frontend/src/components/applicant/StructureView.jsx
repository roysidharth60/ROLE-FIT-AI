import "./applicant.css";

const ROLE_LABELS = {
  name: "Name",
  tagline: "Job title",
  contact: "Contact",
  text: "Paragraph",
  bullet: "Bullet",
  labeled: "Label: value",
  entry_title: "Entry title",
  subline: "Sub-line",
  tech: "Tech line",
  duration: "Duration",
  repo: "Repository",
};

function Field({ field, mode }) {
  if (mode === "slots") {
    return (
      <span className="ap-slot" title={`Original text: ${field.text}`}>
        <span className="ap-slot-name">{field.name}</span>
        <span className="ap-slot-hint">{field.text}</span>
      </span>
    );
  }
  return (
    <span className="ap-chip" title={field.text}>
      <span className="ap-chip-name">{field.name}</span>
      {field.text}
    </span>
  );
}

function Item({ item, mode }) {
  return (
    <div className="ap-item">
      <span className="ap-role">{ROLE_LABELS[item.role] || item.role}</span>
      <div className="ap-fields">
        {item.fields.map((f) => (
          <Field key={f.id} field={f} mode={mode} />
        ))}
      </div>
    </div>
  );
}

// mode "slots": empty placeholders shaped like the template.
// mode "chips": the text we found, shown as pills (dragging comes in a later step).
export default function StructureView({ doc, mode }) {
  if (!doc) return null;
  const head = [doc.name, ...doc.tagline, doc.contact].filter(Boolean);
  return (
    <div className="ap-structure">
      <div className="ap-section">
        <h4>Header</h4>
        {head.map((item) => (
          <Item key={item.id} item={item} mode={mode} />
        ))}
      </div>
      {doc.sections.map((sec) => (
        <div className="ap-section" key={sec.id}>
          <h4>
            {sec.title}
            {sec.canonical ? <small> · {sec.canonical}</small> : <small> · unrecognised</small>}
            {mode === "chips" && sec.suggested_target && <small> · fits a template section</small>}
          </h4>
          {sec.groups.map((grp) => (
            <div className={`ap-group ap-group-${grp.kind}`} key={grp.id}>
              {grp.items.map((item) => (
                <Item key={item.id} item={item} mode={mode} />
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}