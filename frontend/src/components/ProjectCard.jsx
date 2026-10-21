function formatMetric(m) {
  const sign = m.direction === "decrease" ? "-" : "+";
  return `${m.name}: ${m.baseline} → ${m.result} ${m.unit} (${sign}${m.change_pct}%)`;
}

export default function ProjectCard({ project }) {
  const isWork = project.kind === "work";

  return (
    <article className="card">
      <header className="card-head">
        <h3>
          {project.id}. {project.title}
        </h3>
        <span className={`badge ${isWork ? "mandatory" : "preferred"}`}>
          {isWork ? "Work experience" : "Academic project"}
        </span>
      </header>
      <p className="label-note">{project.label}</p>

      <p>{project.scenario}</p>

      <div className="chips">
        {project.stack.map((tool) => (
          <span className="chip" key={tool}>
            {tool}
          </span>
        ))}
      </div>

      <h4>Constraints</h4>
      <ul>
        {project.constraints.map((c, i) => (
          <li key={i}>{c}</li>
        ))}
      </ul>

      <h4>How it was built</h4>
      <p>{project.architecture}</p>

      <h4>CV bullets</h4>
      <ul>
        {project.cv_bullets.map((b, i) => (
          <li key={i}>{b}</li>
        ))}
      </ul>

      {isWork && project.metrics.length > 0 && (
        <>
          <h4>Example figures</h4>
          <ul className="metrics">
            {project.metrics.map((m, i) => (
              <li key={i}>{formatMetric(m)}</li>
            ))}
          </ul>
        </>
      )}

      {project.readiness_statement && (
        <>
          <h4>Readiness</h4>
          <p>{project.readiness_statement}</p>
        </>
      )}

      <h4>Evidence signals (what a candidate would need to show)</h4>
      <ul>
        {project.evidence_signals.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>

      <p className="muted">
        Covers requirements:{" "}
        {project.covers_requirement_ids.map((id) => (
          <span className="chip" key={id}>
            {id}
          </span>
        ))}
      </p>
    </article>
  );
}