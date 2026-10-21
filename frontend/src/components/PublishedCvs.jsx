import { useEffect, useState } from "react";
import { listJobs, getJob, downloadCvDocx } from "../api";
import CvView from "./CvView";

const linkStyle = {
  background: "none",
  border: "none",
  color: "#1d4ed8",
  textDecoration: "underline",
  cursor: "pointer",
  padding: 0,
  font: "inherit",
  fontWeight: "bold",
};

function fileName(job) {
  const base = (job.employer_name || job.title || "reference_cv").replace(/[^A-Za-z0-9]+/g, "_");
  return `${base}_reference_cv.docx`;
}

export default function PublishedCvs({ refreshKey }) {
  const [jobs, setJobs] = useState(null); // null = still loading
  const [listError, setListError] = useState("");
  const [record, setRecord] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [opening, setOpening] = useState(false);
  const [openError, setOpenError] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setListError("");
    listJobs("published")
      .then(setJobs)
      .catch((err) => {
        setListError(err.message);
        setJobs([]);
      });
  }, [refreshKey]);

  async function open(id) {
    setOpenId(id);
    setRecord(null);
    setOpenError("");
    setOpening(true);
    try {
      setRecord(await getJob(id));
    } catch (err) {
      setOpenError(err.message);
    } finally {
      setOpening(false);
    }
  }

  function close() {
    setOpenId(null);
    setRecord(null);
    setOpenError("");
  }

  async function download() {
    setDownloading(true);
    setOpenError("");
    try {
      await downloadCvDocx(record.draft.cv, fileName({ employer_name: record.draft.employer_name, title: record.title }));
    } catch (err) {
      setOpenError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <details open className="card">
      <summary>
        <strong>Published CVs</strong> {jobs && <span className="muted">({jobs.length})</span>}
      </summary>
      {listError && <div className="error-box">{listError}</div>}
      {jobs === null && <p className="muted">Loading...</p>}
      {jobs && jobs.length === 0 && !listError && (
        <p className="muted">Nothing published yet. Publish a job at the end of the page and it appears here.</p>
      )}
      {jobs && jobs.length > 0 && (
        <ul>
          {jobs.map((job) => (
            <li key={job.id}>
              <button style={linkStyle} onClick={() => open(job.id)}>
                {job.employer_name || "(no employer name)"}
              </button>{" "}
              <span className="muted">
                - {job.title}, published {job.published_at ? job.published_at.slice(0, 10) : ""}
              </span>
            </li>
          ))}
        </ul>
      )}

      {openId !== null && (
        <div>
          <hr />
          {opening && <p className="muted">Opening...</p>}
          {openError && <div className="error-box">{openError}</div>}
          {record && (
            <>
              <h3>
                {record.draft.employer_name || "(no employer name)"} - {record.title}
              </h3>
              <div className="row">
                <button onClick={download} disabled={downloading}>
                  {downloading ? "Preparing..." : "Download Word file"}
                </button>
                <button className="secondary" onClick={close}>
                  Close
                </button>
              </div>
              <CvView cv={record.draft.cv} />
            </>
          )}
        </div>
      )}
    </details>
  );
}