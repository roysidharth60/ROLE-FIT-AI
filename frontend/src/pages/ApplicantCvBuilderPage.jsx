import { useEffect, useRef, useState } from "react";
import { analyzeFiles, getStarterPreset, renderCv, saveBlob } from "../components/applicant/applicantApi";
import StructureView from "../components/applicant/StructureView";
import PreviewPane from "../components/applicant/PreviewPane";
import "../components/applicant/applicant.css";

function UploadCard({ title, hint, file, onPick }) {
  return (
    <div className="ap-card">
      <h3>{title}</h3>
      <div style={{ fontSize: 13, color: "#666" }}>{hint}</div>
      <div className="ap-file-name">{file ? `Selected: ${file.name}` : "No file selected"}</div>
      <label className="ap-btn ap-btn-ghost" style={{ display: "inline-block" }}>
        {file ? "Replace file" : "Choose .docx file"}
        <input
          type="file"
          accept=".docx"
          style={{ display: "none" }}
          onChange={(e) => e.target.files[0] && onPick(e.target.files[0])}
        />
      </label>
    </div>
  );
}

export default function ApplicantCvBuilderPage() {
  const [infoFile, setInfoFile] = useState(null);
  const [templateFile, setTemplateFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("preview");

  // Step 2: the mapping (which text goes in which placeholder) and the PDF preview
  const [mapping, setMapping] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [actionError, setActionError] = useState("");
  const [downloading, setDownloading] = useState("");
  const renderCounter = useRef(0);

  function clearPreview() {
    renderCounter.current += 1; // makes any request still running ignore its answer
    setMapping(null);
    setPreviewBusy(false);
    setPreviewError("");
    setActionError("");
    setPreviewUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return "";
    });
  }

  async function handleAnalyze() {
    setLoading(true);
    setError("");
    clearPreview();
    try {
      setResult(await analyzeFiles(infoFile, templateFile));
      setTab("preview");
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadPreset() {
    setActionError("");
    try {
      setMapping(await getStarterPreset(result.session_id));
      setTab("preview");
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleDownload(format) {
    setActionError("");
    setDownloading(format);
    try {
      const blob = await renderCv(result.session_id, mapping, format, true);
      saveBlob(blob, `${result.download_base || "CV"}.${format}`);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setDownloading("");
    }
  }

  // Re-draw the preview about 0.6 s after the last change; keep the old one on screen meanwhile.
  useEffect(() => {
    if (!result || !mapping) return undefined;
    const myId = ++renderCounter.current;
    setPreviewBusy(true);
    const timer = setTimeout(async () => {
      try {
        const blob = await renderCv(result.session_id, mapping, "pdf");
        if (myId !== renderCounter.current) return; // a newer change is already on its way
        const url = URL.createObjectURL(blob);
        setPreviewUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return url;
        });
        setPreviewError("");
      } catch (err) {
        if (myId === renderCounter.current) setPreviewError(err.message);
      } finally {
        if (myId === renderCounter.current) setPreviewBusy(false);
      }
    }, 600);
    return () => clearTimeout(timer);
  }, [mapping, result]);

  return (
    <div className="ap-page">
      <div className="ap-left">
        <UploadCard
          title="1. Information document"
          hint="Word file with the content to use (summary, projects, skills...)."
          file={infoFile}
          onPick={(f) => { setInfoFile(f); setResult(null); clearPreview(); }}
        />
        <UploadCard
          title="2. CV template"
          hint="Word file whose look and layout your CV should copy."
          file={templateFile}
          onPick={(f) => { setTemplateFile(f); setResult(null); clearPreview(); }}
        />
        <button className="ap-btn" disabled={!infoFile || !templateFile || loading} onClick={handleAnalyze}>
          {loading ? "Reading files..." : "Read my files"}
        </button>
        {error && <div className="ap-error">{error}</div>}
        {result && <div className="ap-ok">Both files were read successfully.</div>}
        {result && (
          <div className="ap-card ap-actions">
            <h3>3. Build the CV</h3>
            <button className="ap-btn" onClick={handleLoadPreset}>Load starter preset</button>
            <button className="ap-btn ap-btn-ghost" disabled={!mapping || !!downloading} onClick={() => handleDownload("docx")}>
              {downloading === "docx" ? "Preparing..." : "Download DOCX"}
            </button>
            <button className="ap-btn ap-btn-ghost" disabled={!mapping || !!downloading} onClick={() => handleDownload("pdf")}>
              {downloading === "pdf" ? "Preparing..." : "Download PDF"}
            </button>
            {actionError && <div className="ap-error">{actionError}</div>}
          </div>
        )}
      </div>

      <div className="ap-right">
        {!result && <div className="ap-card">Upload both files and press "Read my files". The placeholders found in your template will appear here.</div>}
        {result && (
          <>
            {result.warnings.length > 0 && (
              <div className="ap-warn">
                Things to check:
                <ul>{result.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
              </div>
            )}
            <div className="ap-tabs">
              {[
                ["preview", "Preview"],
                ["slots", "Template placeholders"],
                ["info", "Info content"],
                ["template", "Template content"],
              ].map(([key, label]) => (
                <button key={key} className={`ap-tab ${tab === key ? "ap-tab-active" : ""}`} onClick={() => setTab(key)}>
                  {label}
                </button>
              ))}
            </div>
            {tab === "preview" && (
              <PreviewPane url={previewUrl} busy={previewBusy} error={previewError} hasMapping={!!mapping} />
            )}
            {tab === "slots" && <StructureView doc={result.template} mode="slots" />}
            {tab === "info" && <StructureView doc={result.sources.info} mode="chips" />}
            {tab === "template" && <StructureView doc={result.sources.template} mode="chips" />}
          </>
        )}
      </div>
    </div>
  );
}
