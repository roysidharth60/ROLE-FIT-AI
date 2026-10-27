
import { useEffect, useState } from "react";
import {
  getJobWatchState,
  saveJobWatchPreferences,
  addJobWatchCompanies,
  flagJobWatchCompany,
  runJobWatchNow,
} from "../jobwatchApi";

export default function JobWatchPage() {
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [state, setState] = useState(null);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [urls, setUrls] = useState("");
  const [busy, setBusy] = useState(false);

  const [include, setInclude] = useState("");
  const [exclude, setExclude] = useState("");
  const [locations, setLocations] = useState("");
  const [interval, setInterval] = useState("10");
  const [tgToken, setTgToken] = useState("");
  const [tgChat, setTgChat] = useState("");

  useEffect(() => {
    if (!state) return;

    const prefs = state.prefs ?? {};
    setInclude(prefs.include ?? "");
    setExclude(prefs.exclude ?? "");
    setLocations(prefs.locations ?? "");
    setInterval(String(prefs.interval ?? 10));
    setTgChat(prefs.tg_chat ?? "");

    // The API masks an existing token. Keep this field empty unless
    // the user wants to enter a replacement token.
    setTgToken("");
  }, [state]);

  async function refresh(secret = password) {
    setError("");

    try {
      const result = await getJobWatchState(secret);
      setState(result);
      setAuthenticated(true);
    } catch (e) {
      setError(e.message || "Could not connect to JobWatch.");
      setAuthenticated(false);
    }
  }

  async function act(action) {
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const result = await action();
      await refresh();

      if (result?.added) {
        setMessage(
          `Added ${result.added.length}; rejected ${
            result.rejected?.length ?? 0
          }.`
        );
      } else {
        setMessage("Action completed.");
      }
    } catch (e) {
      setError(e.message || "The action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setBusy(true);
    await refresh(password);
    setBusy(false);
  }

  if (!authenticated) {
    return (
      <section className="card">
        <h2>JobWatch sign in</h2>
        <p className="muted">
          Enter the JobWatch admin password to manage job alerts.
        </p>

        <form onSubmit={handleSignIn}>
          <label htmlFor="jw-password">Password</label>
          <input
            id="jw-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button type="submit" disabled={!password || busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {error && <p className="error-box">{error}</p>}
      </section>
    );
  }

  return (
    <div>
      <section className="card">
        <h2>JobWatch preferences</h2>
        <p className="muted">
          Configure job keywords, locations, and polling frequency.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();

            act(() =>
              saveJobWatchPreferences(password, {
                include,
                exclude,
                locations,
                interval: Number(interval) || 10,
                tg_token: tgToken,
                tg_chat: tgChat,
              })
            );
          }}
        >
          <label htmlFor="jw-include">Include keywords</label>
          <input
            id="jw-include"
            value={include}
            onChange={(e) => setInclude(e.target.value)}
            placeholder="java, spring boot, fresher"
          />

          <label htmlFor="jw-exclude">Exclude keywords</label>
          <input
            id="jw-exclude"
            value={exclude}
            onChange={(e) => setExclude(e.target.value)}
            placeholder="senior, lead, manager"
          />

          <label htmlFor="jw-locations">Locations</label>
          <input
            id="jw-locations"
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
            placeholder="pune, mumbai, remote, india"
          />

          <label htmlFor="jw-interval">Check interval (minutes)</label>
          <input
            id="jw-interval"
            type="number"
            min="1"
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            required
          />

          <label htmlFor="jw-tg-token">Telegram bot token</label>
          <input
            id="jw-tg-token"
            type="password"
            value={tgToken}
            onChange={(e) => setTgToken(e.target.value)}
            placeholder="Leave blank to keep existing token"
            autoComplete="new-password"
          />

          <label htmlFor="jw-tg-chat">Telegram chat ID</label>
          <input
            id="jw-tg-chat"
            value={tgChat}
            onChange={(e) => setTgChat(e.target.value)}
          />

          <div className="row">
            <button type="submit" disabled={busy}>
              Save preferences
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => act(() => runJobWatchNow(password))}
            >
              Run now
            </button>
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => refresh()}
            >
              Refresh
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Add career pages</h2>
        <p className="muted">Enter one URL per line, up to 50 links.</p>

        <form
          onSubmit={(e) => {
            e.preventDefault();

            act(() => addJobWatchCompanies(password, urls.split("\n")));
            setUrls("");
          }}
        >
          <label htmlFor="jw-urls">Career page URLs</label>
          <textarea
            id="jw-urls"
            rows="5"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            placeholder={
              "https://company.com/careers\nhttps://another-company.com/jobs"
            }
          />
          <button type="submit" disabled={busy || !urls.trim()}>
            Add and auto-detect
          </button>
        </form>
      </section>

      {message && <p className="notice-box">{message}</p>}
      {error && <p className="error-box">{error}</p>}

      <section className="card">
        <h2>Red flag box</h2>

        {state?.flagged?.length ? (
          <ul>
            {state.flagged.map((company, i) => (
              <li key={`${company.name}-${i}`}>
                <strong>{company.name}</strong>
                {" — "}
                {company.reason || "No reason"}
                {" "}
                {company.careers_url && (
                  <a
                    href={company.careers_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Careers page
                  </a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No companies flagged.</p>
        )}
      </section>

      <section className="card">
        <h2>Companies and job results</h2>

        {state?.companies?.length ? (
          state.companies.map((company) => (
            <article
              key={company.name}
              style={{
                borderTop: "1px solid #ddd",
                padding: "12px 0",
              }}
            >
              <h3>{company.name}</h3>

              <p>
                Status: <strong>{company.status || "pending"}</strong>
                {" · "}
                {company.count ?? 0} jobs
                {" · "}
                New: {company.new?.length ?? 0}
                {" · "}
                {company.checked || "Not checked yet"}
              </p>

              {company.careers_url && (
                <p>
                  <a
                    href={company.careers_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {company.careers_url}
                  </a>
                </p>
              )}

              {company.error && (
                <p className="error-box">{company.error}</p>
              )}

              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => {
                  const reason = window.prompt(
                    "What was wrong? (optional)"
                  );

                  if (reason !== null) {
                    act(() =>
                      flagJobWatchCompany(
                        password,
                        company.name,
                        reason
                      )
                    );
                  }
                }}
              >
                Wrong / Flag company
              </button>

              {company.sample?.length > 0 && (
                <ul>
                  {company.sample.map((job, i) => (
                    <li key={`${job.url}-${i}`}>
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {job.title || job.url}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))
        ) : (
          <p className="muted">No companies added yet.</p>
        )}
      </section>
    </div>
  );
}
