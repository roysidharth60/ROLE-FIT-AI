export default function RequirementsTable({ requirements }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Requirement</th>
          <th>Importance</th>
          <th>Quote from the job description</th>
        </tr>
      </thead>
      <tbody>
        {requirements.map((r) => (
          <tr key={r.id}>
            <td>{r.id}</td>
            <td>
              {r.text}
              {r.is_ambiguous && <div className="note-warn">Needs your review: {r.ambiguity_note}</div>}
            </td>
            <td>
              <span className={`badge ${r.importance}`}>{r.importance}</span>
            </td>
            <td className="quote">“{r.source_quote}”</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}