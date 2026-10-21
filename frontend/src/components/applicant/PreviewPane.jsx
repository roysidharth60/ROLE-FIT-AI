import "./applicant.css";

// Shows the CV as a PDF. The previous preview stays visible while a new one is being made.
export default function PreviewPane({ url, busy, error, hasMapping }) {
  return (
    <div className="ap-preview">
      {error && <div className="ap-error">{error}</div>}
      {!hasMapping && !url && (
        <div className="ap-card">
          No preview yet. Press <b>Load starter preset</b> on the left to fill the template with the
          suggested mapping.
        </div>
      )}
      {url && (
        <div className="ap-preview-wrap">
          {busy && <div className="ap-preview-busy">Updating preview...</div>}
          <iframe className="ap-preview-frame" title="CV preview" src={`${url}#toolbar=0&navpanes=0`} />
        </div>
      )}
      {!url && hasMapping && busy && <div className="ap-card">Building your preview...</div>}
    </div>
  );
}
