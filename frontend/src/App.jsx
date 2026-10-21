import { useState } from "react";
import "./App.css";
import EmployerPage from "./pages/EmployerPage";
import ApplicantCvBuilderPage from "./pages/ApplicantCvBuilderPage";

export default function App() {
  // "employer" or "applicant". Both pages stay mounted and one is hidden,
  // so switching tabs never wipes what the employer was working on.
  const [view, setView] = useState("employer");

  return (
    <main className="page">
      <header className="top">
        <h1>RoleFit AI</h1>
        <p className="muted">
          {view === "employer" ? "Employer Job Profile Builder" : "Applicant CV Builder"}
        </p>
        <div className="row">
          <button
            className={view === "employer" ? "" : "secondary"}
            onClick={() => setView("employer")}
          >
            Employer
          </button>
          <button
            className={view === "applicant" ? "" : "secondary"}
            onClick={() => setView("applicant")}
          >
            Applicant
          </button>
        </div>
      </header>

      <div hidden={view !== "employer"}>
        <EmployerPage />
      </div>
      <div hidden={view !== "applicant"}>
        <ApplicantCvBuilderPage />
      </div>
    </main>
  );
}