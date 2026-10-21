export default function Checklist({ items }) {
  if (!items || items.length === 0) return null;
  const passed = items.filter((i) => i.passed).length;
  return (
    <div className="notice-box">
      <strong>
        CV checklist: {passed} of {items.length} passed
      </strong>
      <ul style={{ listStyle: "none", paddingLeft: 0 }}>
        {items.map((item) => (
          <li key={item.id}>
            <span className={`badge ${item.passed ? "mandatory" : "error"}`}>{item.passed ? "PASS" : "FAIL"}</span>{" "}
            {item.label} <span className="muted">- {item.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}