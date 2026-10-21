const API = "http://127.0.0.1:8000";

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API}${path}`, options);
  } catch {
    throw new Error("Cannot reach the backend. Is backend\\run.py running?");
  }

  if (!response.ok) {
    let message = `The request failed (status ${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (body.detail) {
        message = "The request was not valid: " + JSON.stringify(body.detail).slice(0, 300);
      }
    } catch {
      // the response had no JSON body; keep the generic message
    }
    throw new Error(message);
  }
  return response;
}

async function postJson(path, payload) {
  const response = await request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

// Old one-shot endpoint, kept for now but no longer used by the page
export function generateJobDraft(jdText) {
  return postJson("/api/jobs/generate", { jd_text: jdText });
}

// Staged flow, step 1: extract requirements from the job description
export function getRequirements(jdText) {
  return postJson("/api/jobs/requirements", { jd_text: jdText });
}




// Staged flow, step 2: plan three different starting situations and who covers which requirement
export function getPlan(jdText, requirements) {
  return postJson("/api/jobs/plan", { jd_text: jdText, requirements });
}




// Staged flow, step 3: write ONE reference project (P1, P2 or P3)
export function getProject({ jdText, requirements, projectId, premise, employerName, targets, others, employerNote }) {
  return postJson("/api/jobs/project", {
    jd_text: jdText,
    requirements,
    project_id: projectId,
    premise,
    employer_name: employerName,
    targets,
    others,
    employer_note: employerNote,
  });
}




// Staged flow, step 4: the ideal profile (title, summary, skill groups)
export function getProfile({ jdText, requirements, projectStacks, employerName, part, current, employerNote, summarySentences }) {
  return postJson("/api/jobs/profile", {
    jd_text: jdText,
    requirements,
    project_stacks: projectStacks,
    employer_name: employerName,
    part,
    current,
    employer_note: employerNote,
    summary_sentences: summarySentences,
  });
}

// Staged flow, step 5: assemble the CV from the current parts (no model call) and re-run every check
export function buildCv({ profile, projects, requirements }) {
  return postJson("/api/jobs/build-cv", { profile, projects, requirements });
}




// Rewrite the CV bullets of ONE project following the employer's own note (figures, wording, details)
export function rewriteBullets({ projectId, kind, title, scenario, stack, currentBullets, employerNote, employerName, bulletCount, maxWords }) {
  return postJson("/api/jobs/bullets", {
    project_id: projectId,
    kind,
    title,
    scenario,
    stack,
    current_bullets: currentBullets,
    employer_note: employerNote,
    employer_name: employerName,
    bullet_count: bulletCount,
    max_words: maxWords,
  });
}



// Save a reviewed draft. Publishing needs publish=true AND confirmPublish=true (the API enforces it).
export function saveJob({ title, draft, publish, confirmPublish }) {
  return postJson("/api/jobs", { title, draft, publish, confirm_publish: confirmPublish });
}

export async function listJobs(status) {
  const query = status ? `?status=${status}` : "";
  const response = await request(`/api/jobs${query}`);
  return response.json();
}

export async function getJob(id) {
  const response = await request(`/api/jobs/${id}`);
  return response.json();
}

// Builds the Word file from the given CV on the backend and saves it in the browser
export async function downloadCvDocx(cv, filename) {
  const response = await request("/api/jobs/cv-docx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cv),
  });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}