
import { useState } from "react";
import "./App.css";
import EmployerPage from "./pages/EmployerPage";
import ApplicantCvBuilderPage from "./pages/ApplicantCvBuilderPage";
import JobWatchPage from "./pages/JobWatchPage";

export default function App() {
  const [view, setView] = useState("employer");

  const descriptions = {
    employer: "Employer Job Profile Builder",
    applicant: "Applicant CV Builder",
    jobwatch: "Continuous Job Alerts",
  };

  return (
    <main className="page">
      <header className="top">
        <h1>RoleFit AI</h1>
        <p className="muted">{descriptions[view]}</p>

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

          <button
            className={view === "jobwatch" ? "" : "secondary"}
            onClick={() => setView("jobwatch")}
          >
            JobWatch
          </button>
        </div>
      </header>

      <div hidden={view !== "employer"}>
        <EmployerPage />
      </div>

      <div hidden={view !== "applicant"}>
        <ApplicantCvBuilderPage />
      </div>

      <div hidden={view !== "jobwatch"}>
        <JobWatchPage />
      </div>
    </main>
  );
}
