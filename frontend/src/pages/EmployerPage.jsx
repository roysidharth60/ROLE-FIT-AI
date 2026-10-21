import { useEffect, useState } from "react";
import { getRequirements, getPlan, getProject, getProfile, buildCv, saveJob } from "../api";
import RequirementsTable from "../components/RequirementsTable";
import ProjectCard from "../components/ProjectCard";
import CvDraft from "../components/CvDraft";
import PublishedCvs from "../components/PublishedCvs";
import { SAMPLE_JD } from "../sampleJD";

const MIN_CHARS = 50;
const MAX_NOTE = 300;

export default function EmployerPage() {
  const [title, setTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [result, setResult] = useState(null); // { requirements, warnings, usage }
  const [confirmed, setConfirmed] = useState(false);
  const [plan, setPlan] = useState(null); // { employer_name, premises, coverage_plan, usage }
  const [accepted, setAccepted] = useState([]); // projects the employer accepted, in order
  const [candidate, setCandidate] = useState(null); // { project, issues, attempts, usage }
  const [note, setNote] = useState("");
  const [profileRes, setProfileRes] = useState(null); // { profile, issues, usage }
  const [profileNote, setProfileNote] = useState("");
  const [summarySentences, setSummarySentences] = useState(2);
  const [profileAccepted, setProfileAccepted] = useState(false);
  const [cv, setCv] = useState(null);
  const [cvDirty, setCvDirty] = useState(false); // CV edits not yet re-checked
  const [employerName, setEmployerName] = useState("");
  const [confirmPublish, setConfirmPublish] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saved, setSaved] = useState(null); // { id, status, ... } from the last save
  const [listVersion, setListVersion] = useState(0); // bumps to refresh the Published CVs list
  const [loading, setLoading] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");

  // A simple stopwatch while the model works, so the page never looks frozen
  useEffect(() => {
    if (!loading) return undefined;
    setSeconds(0);
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [loading]);

  function resetFrom() {
    setConfirmed(false);
    setPlan(null);
    setAccepted([]);
    setCandidate(null);
    setNote("");
    setProfileRes(null);
    setProfileNote("");
    setSummarySentences(2);
    setProfileAccepted(false);
    setCv(null);
    setCvDirty(false);
    setEmployerName("");
    setConfirmPublish(false);
    setSaveError("");
    setSaved(null);
    setError("");
  }

  async function handleExtract() {
    resetFrom();
    setResult(null);
    setLoading(true);
    try {
      setResult(await getRequirements(jdText));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Writes project number `index` (0, 1 or 2). `acceptedList` are the projects already accepted.
  async function runProject(index, acceptedList, employerNote, planData) {
    const pid = `P${index + 1}`;
    setError("");
    setLoading(true);
    try {
      const res = await getProject({
        jdText,
        requirements: result.requirements,
        projectId: pid,
        premise: planData.premises[index],
        employerName: planData.employer_name,
        targets: planData.coverage_plan[pid] || [],
        others: acceptedList,
        employerNote,
      });
      setCandidate(res);
    } catch (err) {
      setError(err.message); // the previous candidate (if any) stays on screen
    } finally {
      setLoading(false);
    }
  }

  // part: "all" | "summary" | "skills". For summary/skills the current profile is sent so the rest is kept.
  async function runProfile(part, current, employerNote, projectsList, planData) {
    setError("");
    setLoading(true);
    try {
      const res = await getProfile({
        jdText,
        requirements: result.requirements,
        projectStacks: projectsList.map((p) => p.stack),
        employerName: planData.employer_name,
        part,
        current,
        employerNote,
        summarySentences,
      });
      setProfileRes(res);
    } catch (err) {
      setError(err.message); // the previous profile (if any) stays on screen
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    setError("");
    setConfirmed(true);
    setLoading(true);
    let planData = null;
    try {
      planData = await getPlan(jdText, result.requirements);
      setPlan(planData);
      setEmployerName(planData.employer_name || "");
    } catch (err) {
      setError(err.message);
      setConfirmed(false); // the Confirm button comes back so you can retry
    } finally {
      setLoading(false);
    }
    if (planData) {
      await runProject(0, [], "", planData); // start P1 straight away
    }
  }

  function handleRegenerate() {
    runProject(accepted.length, accepted, note.trim(), plan);
  }

  function handleAccept() {
    const next = [...accepted, candidate.project];
    setAccepted(next);
    setCandidate(null);
    setNote("");
    if (next.length < 3) {
      runProject(next.length, next, "", plan);
    } else {
      runProfile("all", null, "", next, plan); // all projects done: write the profile
    }
  }

  function handleRegenerateProfile(part) {
    runProfile(part, profileRes ? profileRes.profile : null, profileNote.trim(), accepted, plan);
  }

  async function handleAcceptProfile() {
    setError("");
    setProfileAccepted(true);
    setLoading(true);
    try {
      setCv(await buildCv({ profile: profileRes.profile, projects: accepted, requirements: result.requirements }));
    } catch (err) {
      setError(err.message);
      setProfileAccepted(false); // the Accept button comes back so you can retry
    } finally {
      setLoading(false);
    }
  }

  // Called by the CV draft after the employer edited it: rebuild the CV and re-run every check
  async function handleRecheck(editedProfile, editedProjects) {
    setError("");
    setLoading(true);
    try {
      const newCv = await buildCv({
        profile: editedProfile,
        projects: editedProjects,
        requirements: result.requirements,
      });
      setProfileRes((prev) => ({ ...prev, profile: editedProfile }));
      setAccepted(editedProjects);
      setCv(newCv);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Save as draft (publish=false) or publish (publish=true plus the explicit confirmation)
  async function handleSave(publish) {
    setSaveError("");
    setSaved(null);
    setSaving(true);
    try {
      const res = await saveJob({
        title: title.trim(),
        draft: {
          requirements: result.requirements,
          extraction_warnings: result.warnings,
          projects: accepted,
          ideal_profile: profileRes.profile,
          cv,
          issues: [],
          coverage_plan: plan.coverage_plan,
          employer_name: employerName.trim(),
        },
        publish,
        confirmPublish: publish && confirmPublish,
      });
      setSaved(res);
      setListVersion((v) => v + 1);
      setConfirmPublish(false);
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function handleStartOver() {
    resetFrom();
    setResult(null);
  }

  function useSample() {
    setTitle("Healthcare Data Analyst");
    setJdText(SAMPLE_JD);
  }

  const locked = loading || result !== null;
  const canExtract = title.trim().length > 0 && jdText.trim().length >= MIN_CHARS;
  const currentNumber = accepted.length + 1; // which project is being worked on (1 to 3)
  const allAccepted = accepted.length === 3;
  const alreadyPublished = saved !== null && saved.status === "published";
  const saveBlocked =
    saving ||
    loading ||
    !cv ||
    cvDirty ||
    alreadyPublished ||
    employerName.trim().length < 2 ||
    title.trim().length < 3;

  // Progress and errors appear right under the heading of the stage that is active
  const status = (
    <>
      {loading && (
        <p className="muted">
          Working... {seconds}s.{" "}
          {plan && !allAccepted && `Writing project P${currentNumber}; this can take up to a minute.`}
        </p>
      )}
      {error && <div className="error-box">{error}</div>}
    </>
  );

  return (
    <section>
      <PublishedCvs refreshKey={listVersion} />

      <h2>1. Job title and description</h2>
      <input
        className="jd-input"
        type="text"
        maxLength={100}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Job title, for example Healthcare Data Analyst"
        disabled={locked}
      />
      <textarea
        className="jd-input"
        rows={10}
        value={jdText}
        onChange={(e) => setJdText(e.target.value)}
        placeholder="Paste the job description here..."
        disabled={locked}
      />
      <div className="row">
        <button onClick={handleExtract} disabled={locked || !canExtract}>
          {loading && !result ? "Extracting..." : "Extract requirements"}
        </button>
        <button className="secondary" onClick={useSample} disabled={locked}>
          Use sample job description
        </button>
        {result && (
          <button className="secondary" onClick={handleStartOver} disabled={loading || saving}>
            Start over
          </button>
        )}
        {!canExtract && !locked && (
          <span className="muted">Enter a job title and at least {MIN_CHARS} characters of description.</span>
        )}
      </div>

      {!plan && status}

      {result && (
        <>
          <h2>2. Requirements</h2>
          <p className="muted">
            Check these before anything else. Everything below is built on them.
            {result.usage &&
              ` (Model use: ${result.usage.input_tokens} tokens in, ${result.usage.output_tokens} tokens out.)`}
          </p>
          <RequirementsTable requirements={result.requirements} />

          {result.warnings.length > 0 && (
            <div className="notice-box">
              <strong>Things to review</strong>
              <ul>
                {result.warnings.map((message, i) => (
                  <li key={i}>
                    <span className="badge warning">warning</span> {message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!confirmed ? (
            <div className="row">
              <button onClick={handleConfirm} disabled={loading}>
                Confirm requirements
              </button>
              <span className="muted">Confirming starts the plan. Not happy? Click Start over.</span>
            </div>
          ) : (
            <p>
              <strong>Requirements confirmed.</strong>
            </p>
          )}
        </>
      )}

      {plan && (
        <>
          <h2>3. Plan for the reference projects</h2>
          <p className="muted">
            Three different starting situations, so the projects do not repeat each other.
            {plan.employer_name && ` Employer name found in the description: ${plan.employer_name}.`}
          </p>
          {plan.premises.map((premise, i) => {
            const pid = `P${i + 1}`;
            const covers = plan.coverage_plan[pid] || [];
            return (
              <div className="card" key={pid}>
                <h3>
                  {pid} ({i === 2 ? "academic" : "work"}): {premise.title}
                </h3>
                <p>{premise.situation}</p>
                <div>
                  <span className="muted">Planned to cover: </span>
                  {covers.map((rid) => (
                    <span className="chip" key={rid}>
                      {rid}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}

          <h2>4. Reference projects</h2>
          <p className="muted">
            Review each project. If you are not satisfied, add an optional note and click Regenerate. When it is
            good, click Accept to move on.
          </p>
          {!allAccepted && status}
          {error && !candidate && !loading && !allAccepted && (
            <div className="row">
              <button onClick={handleRegenerate}>Try P{currentNumber} again</button>
            </div>
          )}

          {accepted.map((project) => (
            <div key={project.id}>
              <p>
                <span className="badge mandatory">accepted</span>
              </p>
              <ProjectCard project={project} />
            </div>
          ))}

          {candidate && (
            <div>
              <p>
                <strong>Project P{currentNumber} - waiting for your decision</strong>{" "}
                <span className="muted">
                  (attempts: {candidate.attempts}
                  {candidate.usage &&
                    `, ${candidate.usage.input_tokens} tokens in, ${candidate.usage.output_tokens} out`}
                  )
                </span>
              </p>
              <ProjectCard project={candidate.project} />

              {candidate.issues.length > 0 && (
                <div className="notice-box">
                  <strong>Things to review in this project</strong>
                  <ul>
                    {candidate.issues.map((n, i) => (
                      <li key={i}>
                        <span className={`badge ${n.severity}`}>{n.severity}</span> {n.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <textarea
                className="jd-input"
                rows={2}
                maxLength={MAX_NOTE}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional note for Regenerate, for example: focus on billing disputes, use Tableau"
                disabled={loading}
              />
              <p className="muted">
                {note.length}/{MAX_NOTE} characters. Your note decides. The writer follows it even where it differs
                from the usual style and length rules. Rule problems are only shown as warnings.
              </p>
              <div className="row">
                <button className="secondary" onClick={handleRegenerate} disabled={loading}>
                  Regenerate P{currentNumber}
                </button>
                <button onClick={handleAccept} disabled={loading}>
                  {currentNumber < 3 ? `Accept P${currentNumber} and continue` : "Accept P3"}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {allAccepted && (
        <>
          <h2>5. Ideal candidate profile</h2>
          <p className="muted">
            The summary and skills for the reference CV. Not happy with one part? Choose the summary length, add an
            optional note and regenerate just that part. You can also edit everything by hand in the CV draft below.
          </p>
          {!profileAccepted && status}
          {error && !profileRes && !loading && !profileAccepted && (
            <div className="row">
              <button onClick={() => runProfile("all", null, "", accepted, plan)}>Try the profile again</button>
            </div>
          )}

          {profileRes && (
            <div className="card">
              <h3>{profileRes.profile.target_title}</h3>
              <h4>Summary</h4>
              <p>{profileRes.profile.summary}</p>
              <h4>Skills</h4>
              {profileRes.profile.skill_groups.map((group) => (
                <div key={group.label}>
                  <strong>{group.label}: </strong>
                  {group.items.map((item) => (
                    <span className="chip" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              ))}
              {profileRes.usage && (
                <p className="muted">
                  ({profileRes.usage.input_tokens} tokens in, {profileRes.usage.output_tokens} out)
                </p>
              )}

              {profileRes.issues.length > 0 && (
                <div className="notice-box">
                  <strong>Things to review in the profile</strong>
                  <ul>
                    {profileRes.issues.map((n, i) => (
                      <li key={i}>
                        <span className={`badge ${n.severity}`}>{n.severity}</span> {n.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!profileAccepted && (
                <>
                  <div className="row">
                    <label>
                      Summary length:{" "}
                      <select
                        value={summarySentences}
                        onChange={(e) => setSummarySentences(Number(e.target.value))}
                        disabled={loading}
                      >
                        {[1, 2, 3, 4].map((n) => (
                          <option key={n} value={n}>
                            {n} sentence{n > 1 ? "s" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                    <span className="muted">Used when you click Regenerate summary.</span>
                  </div>
                  <textarea
                    className="jd-input"
                    rows={2}
                    maxLength={MAX_NOTE}
                    value={profileNote}
                    onChange={(e) => setProfileNote(e.target.value)}
                    placeholder="Optional note, for example: mention weekly reporting for clinic managers"
                    disabled={loading}
                  />
                  <p className="muted">{profileNote.length}/{MAX_NOTE} characters.</p>
                  <div className="row">
                    <button className="secondary" onClick={() => handleRegenerateProfile("summary")} disabled={loading}>
                      Regenerate summary
                    </button>
                    <button className="secondary" onClick={() => handleRegenerateProfile("skills")} disabled={loading}>
                      Regenerate skills
                    </button>
                    <button onClick={handleAcceptProfile} disabled={loading}>
                      Accept profile and build CV
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}

      {profileAccepted && (
        <>
          <h2>6. Reference CV draft</h2>
          {status}
          <CvDraft
            profile={profileRes.profile}
            projects={accepted}
            cv={cv}
            busy={loading}
            onRecheck={handleRecheck}
            employerName={plan ? plan.employer_name : ""}
            onDirtyChange={setCvDirty}
          />
        </>
      )}

      {profileAccepted && cv && (
        <>
          <h2>7. Save and publish</h2>
          <p className="muted">
            The employer name is what appears in the Published CVs list at the top of the page. The CV that is
            saved is the checked version shown above.
          </p>
          <input
            className="jd-input"
            type="text"
            maxLength={100}
            value={employerName}
            onChange={(e) => setEmployerName(e.target.value)}
            placeholder="Employer name, for example Harbor Light Clinics"
            disabled={saving || alreadyPublished}
          />
          {cvDirty && (
            <p className="muted">
              You have CV edits that are not checked yet. Click "Update CV and re-run checks" first, so the saved CV
              is the one you see.
            </p>
          )}
          <label>
            <input
              type="checkbox"
              checked={confirmPublish}
              onChange={(e) => setConfirmPublish(e.target.checked)}
              disabled={saving || alreadyPublished}
            />{" "}
            I have reviewed the requirements, projects and CV, and I confirm that they may be published.
          </label>
          <div className="row">
            <button className="secondary" onClick={() => handleSave(false)} disabled={saveBlocked}>
              Save as draft
            </button>
            <button onClick={() => handleSave(true)} disabled={saveBlocked || !confirmPublish}>
              {saving ? "Saving..." : "Publish"}
            </button>
          </div>
          {saveError && <div className="error-box">{saveError}</div>}
          {saved && (
            <p>
              <strong>{saved.status === "published" ? "Published." : "Draft saved."}</strong>{" "}
              {saved.status === "published"
                ? `Open "Published CVs" at the top of the page and click ${employerName.trim()}. Click Start over to build another job.`
                : "Drafts are not listed yet; publish when you are ready."}
            </p>
          )}
        </>
      )}
    </section>
  );
}