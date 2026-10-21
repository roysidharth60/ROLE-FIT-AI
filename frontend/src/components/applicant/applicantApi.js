// Talks to the FastAPI backend. Change API_URL if your backend runs elsewhere.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function analyzeFiles(infoFile, templateFile) {
  const form = new FormData();
  form.append("info", infoFile);
  form.append("template", templateFile);

  let response;
  try {
    response = await fetch(`${API_URL}/api/applicant/analyze`, { method: "POST", body: form });
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }
  if (!response.ok) {
    let message = "Something went wrong while reading your files.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep the default message */
    }
    throw new Error(message);
  }
  return response.json();
}

// ---------- Step 2: starter mapping, preview and downloads ----------

async function errorFrom(response, fallback) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* keep the fallback */
  }
  return fallback;
}

// The hand-made mapping (what text goes into which placeholder) for this session.
export async function getStarterPreset(sessionId) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/applicant/starter-preset/${sessionId}`);
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }
  if (!response.ok) throw new Error(await errorFrom(response, "Could not load the suggested mapping."));
  return response.json();
}

// Build the CV. format is "pdf" (preview) or "docx" (download). Returns a Blob.
export async function renderCv(sessionId, mapping, format = "pdf", strict = false) {
  let response;
  try {
    response = await fetch(
      `${API_URL}/api/applicant/render?format=${format}${strict ? "&strict=true" : ""}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, mapping }),
      }
    );
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }
  if (!response.ok) throw new Error(await errorFrom(response, "The CV could not be built."));
  return response.blob();
}

// Save a Blob as a file in the user's Downloads folder.
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
