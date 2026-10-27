const API = "/jobwatch/api";

function authHeaders(password, json = false) {
  const headers = {
    Authorization: `Basic ${btoa(`admin:${password}`)}`,
  };

  if (json) headers["Content-Type"] = "application/json";
  return headers;
}

async function request(path, password, payload) {
  const options = {
    headers: authHeaders(password, payload !== undefined),
  };

  if (payload !== undefined) {
    options.method = "POST";
    options.body = JSON.stringify(payload);
  }

  const response = await fetch(`${API}${path}`, options);

  if (response.status === 401) {
    throw new Error("Incorrect JobWatch password.");
  }

  if (!response.ok) {
    throw new Error(`JobWatch request failed (${response.status}).`);
  }

  return response.json();
}

export function getJobWatchState(password) {
  return request("/state", password);
}

export function saveJobWatchPreferences(password, preferences) {
  return request("/prefs", password, preferences);
}

export function addJobWatchCompanies(password, urls) {
  return request("/companies/bulk", password, { urls });
}

export function flagJobWatchCompany(password, name, reason = "") {
  return request("/flag", password, { name, reason });
}

export function runJobWatchNow(password) {
  return request("/run", password, {});
}