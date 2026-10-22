"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  BriefcaseBusiness,
  Users,
  FileCheck2,
  ShieldCheck,
  Plus,
  RefreshCw,
  LogOut,
  LoaderCircle,
  AlertCircle,
  BrainCircuit,
} from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type CurrentUser = {
  id: number;
  email: string;
  employee_id: string;
  role: string;
  is_active: boolean;
};

type Job = {
  id: number;
  job_code: string;
  title: string;
  department_id: number;
  description: string;
  required_skills: string;
  preferred_skills?: string | null;
  minimum_experience_years: number;
  status: string;
};

type Candidate = {
  id: number;
  candidate_code: string;
  full_name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  resume_filename?: string | null;
};

type Application = {
  id: number;
  job_id: number;
  candidate_id: number;
  application_status: string;
  ai_fit_score?: number | null;
  matched_skills?: string | string[] | null;
  missing_skills?: string | string[] | null;
  ai_summary?: string | null;
  ai_recommendation?: string | null;
  human_review_status?: string | null;
  reviewed_by?: string | null;
  review_notes?: string | null;
};

type HiringFormState = {
  gender: string;
  age: string;
  job_level: string;
  work_location: string;
  joining_date: string;
  tenure_years_at_period_start: string;
  education: string;
  marital_status: string;
  annual_base_salary_inr: string;
  manager_id: string;
};

function createHiringFormState(): HiringFormState {
  return {
    gender: "",
    age: "",
    job_level: "",
    work_location: "",
    joining_date: "",
    tenure_years_at_period_start: "0",
    education: "",
    marital_status: "",
    annual_base_salary_inr: "",
    manager_id: "",
  };
}

function toSkillList(
  value: string | string[] | null | undefined
): string[] {
  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    return value
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);
  }

  return [];
}

type Tab = "jobs" | "candidates" | "applications";

const inputClassName = "recruitment-input";

export default function RecruitmentPage() {
  const router = useRouter();

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("jobs");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [jobForm, setJobForm] = useState({
    job_code: "",
    title: "",
    department_id: "",
    description: "",
    required_skills: "",
    preferred_skills: "",
    minimum_experience_years: "0",
  });

  const [candidateForm, setCandidateForm] = useState({
    candidate_code: "",
    full_name: "",
    email: "",
    phone: "",
    location: "",
    resume_filename: "",
    resume_text: "",
  });

  const [applicationForm, setApplicationForm] = useState({
    job_id: "",
    candidate_id: "",
  });

  const [reviewForms, setReviewForms] = useState<
    Record<number, { review_status: string; review_notes: string }>
  >({});

  const [hiringForms, setHiringForms] = useState<
    Record<number, HiringFormState>
  >({});
  const [hiringApplicationId, setHiringApplicationId] = useState<number | null>(null);

  const [showJobForm, setShowJobForm] = useState(false);
  const [showCandidateForm, setShowCandidateForm] = useState(false);
  const [showApplicationForm, setShowApplicationForm] = useState(false);

  const getToken = () =>
    typeof window !== "undefined"
      ? sessionStorage.getItem("orbithr_access_token")
      : null;

  const apiRequest = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const token = getToken();

      if (!token) {
        throw new Error("Your session has expired. Please sign in again.");
      }

      const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          Authorization: `Bearer ${token}`,
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...options.headers,
        },
        cache: "no-store",
      });

      const body = await response.json().catch(() => null);

      if (response.status === 401 || response.status === 403) {
        throw new Error(
          response.status === 403
            ? "Your account does not have permission to perform this action."
            : "Your session has expired. Please sign in again.",
        );
      }

      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : `Request failed (HTTP ${response.status}).`,
        );
      }

      return body;
    },
    [],
  );

  const loadWorkspace = useCallback(
    async (showRefresh = false) => {
      if (showRefresh) setRefreshing(true);
      else setLoading(true);

      setError("");

      try {
        const token = getToken();

        if (!token) {
          router.replace("/login");
          return;
        }

        const currentUser: CurrentUser = await apiRequest("/api/auth/me");

        if (!currentUser.is_active) {
          sessionStorage.removeItem("orbithr_access_token");
          sessionStorage.removeItem("orbithr_user");
          router.replace("/login");
          return;
        }

        const allowedRoles = ["RECRUITER", "HR", "ADMIN"];

        if (!allowedRoles.includes(currentUser.role.toUpperCase())) {
          setUser(currentUser);
          setError(
            "Recruitment access is restricted to authorized recruiters, HR, and administrators.",
          );
          return;
        }

        setUser(currentUser);
        sessionStorage.setItem("orbithr_user", JSON.stringify(currentUser));

        const [jobData, candidateData, applicationData] = await Promise.all([
          apiRequest("/api/recruitment/jobs"),
          apiRequest("/api/recruitment/candidates"),
          apiRequest("/api/recruitment/applications"),
        ]);

        setJobs(Array.isArray(jobData) ? jobData : []);
        setCandidates(Array.isArray(candidateData) ? candidateData : []);
        setApplications(
          Array.isArray(applicationData) ? applicationData : [],
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unable to load recruitment.";

        if (
          message.includes("session has expired") ||
          message.includes("sign in again")
        ) {
          sessionStorage.removeItem("orbithr_access_token");
          sessionStorage.removeItem("orbithr_user");
          router.replace("/login");
          return;
        }

        setError(message);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiRequest, router],
  );

  useEffect(() => {
  const timer = window.setTimeout(() => {
    void loadWorkspace();
  }, 0);

  return () => window.clearTimeout(timer);
}, [loadWorkspace]);

  async function handleCreateJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setNotice("");

    try {
      const payload = {
        ...jobForm,
        department_id: Number(jobForm.department_id),
        minimum_experience_years: Number(
          jobForm.minimum_experience_years,
        ),
        required_skills: jobForm.required_skills,
        preferred_skills: jobForm.preferred_skills || null,
        status: "Open",
      };

      await apiRequest("/api/recruitment/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setJobForm({
        job_code: "",
        title: "",
        department_id: "",
        description: "",
        required_skills: "",
        preferred_skills: "",
        minimum_experience_years: "0",
      });

      setShowJobForm(false);
      setNotice("Job opening created successfully.");
      await loadWorkspace(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create job.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateCandidate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setNotice("");

    try {
      const payload = {
        ...candidateForm,
        phone: candidateForm.phone || null,
        location: candidateForm.location || null,
        resume_filename: candidateForm.resume_filename || null,
        resume_text: candidateForm.resume_text || null,
      };

      await apiRequest("/api/recruitment/candidates", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setCandidateForm({
        candidate_code: "",
        full_name: "",
        email: "",
        phone: "",
        location: "",
        resume_filename: "",
        resume_text: "",
      });

      setShowCandidateForm(false);
      setNotice("Candidate registered successfully.");
      await loadWorkspace(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to register candidate.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setNotice("");

    try {
      await apiRequest("/api/recruitment/applications", {
        method: "POST",
        body: JSON.stringify({
          job_id: Number(applicationForm.job_id),
          candidate_id: Number(applicationForm.candidate_id),
          application_status: "Applied",
        }),
      });

      setApplicationForm({ job_id: "", candidate_id: "" });
      setShowApplicationForm(false);
      setNotice(
        "Application created. Screening results are advisory and require human review.",
      );
      setActiveTab("applications");
      await loadWorkspace(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create application.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReview(
    event: FormEvent<HTMLFormElement>,
    applicationId: number,
  ) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setNotice("");

    const review = reviewForms[applicationId] ?? {
      review_status: "Review Required",
      review_notes: "",
    };

    try {
      await apiRequest(
        `/api/recruitment/applications/${applicationId}/review`,
        {
          method: "POST",
          body: JSON.stringify({
            review_status: review.review_status,
            review_notes: review.review_notes || null,
          }),
        },
      );

      setNotice(`Application #${applicationId} review saved.`);
      await loadWorkspace(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to review application.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirmHire(
    event: FormEvent<HTMLFormElement>,
    applicationId: number,
  ) {
    event.preventDefault();

    if (!user || !["HR", "ADMIN"].includes(user.role.toUpperCase())) {
      setError("Only HR or Admin can confirm a hire.");
      return;
    }

    const form = hiringForms[applicationId] ?? createHiringFormState();

    if (!form.joining_date) {
      setError("Enter the HR-confirmed joining date before confirming the hire.");
      return;
    }

    const confirmed = window.confirm(
      `Confirm hiring for ${candidateName(candidates, applications.find((item) => item.id === applicationId)?.candidate_id ?? -1)}? This creates an employee record and onboarding case.`,
    );
    if (!confirmed) return;

    setSubmitting(true);
    setError("");
    setNotice("");

    try {
      const result = await apiRequest(
        `/api/recruitment/applications/${applicationId}/hire`,
        {
          method: "POST",
          body: JSON.stringify({
            gender: form.gender.trim(),
            age: Number(form.age),
            job_level: form.job_level.trim(),
            work_location: form.work_location.trim(),
            joining_date: form.joining_date,
            tenure_years_at_period_start: Number(
              form.tenure_years_at_period_start || "0",
            ),
            education: form.education.trim(),
            marital_status: form.marital_status.trim(),
            annual_base_salary_inr: Number(form.annual_base_salary_inr),
            manager_id: form.manager_id.trim() || null,
          }),
        },
      );

      setHiringApplicationId(null);
      setHiringForms((current) => {
        const next = { ...current };
        delete next[applicationId];
        return next;
      });
      setNotice(
        `Hire confirmed. Employee ${result.employee_id} and onboarding case #${result.onboarding_case_id} created.`,
      );
      await loadWorkspace(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to confirm hire.");
    } finally {
      setSubmitting(false);
    }
  }

  function signOut() {
    sessionStorage.removeItem("orbithr_access_token");
    sessionStorage.removeItem("orbithr_user");
    router.replace("/login");
  }

  const pendingReviews = applications.filter(
    (application) =>
      !["APPROVED", "REJECTED"].includes(
        (application.human_review_status ?? "Pending").toUpperCase(),
      ),
  ).length;

  if (loading) {
    return (
      <main className="recruitment-shell">
        <div className="recruitment-loading">
          <LoaderCircle className="recruitment-spin" size={28} />
          <p>Verifying access and loading recruitment workspace...</p>
        </div>
      </main>
    );
  }

  const allowed =
    user && ["RECRUITER", "HR", "ADMIN"].includes(user.role.toUpperCase());
  const canConfirmHire =
    user && ["HR", "ADMIN"].includes(user.role.toUpperCase());

  return (
    <main className="recruitment-shell">
      <header className="recruitment-topbar">
        <button
          className="recruitment-back"
          onClick={() => router.push("/")}
          type="button"
        >
          <ArrowLeft size={16} /> Dashboard
        </button>

        <div className="recruitment-brand">
          <span className="recruitment-brand-mark">
            <BrainCircuit size={19} />
          </span>
          <span>
            ORBIT HR <small>/ TALENT INTELLIGENCE</small>
          </span>
        </div>

        <button className="recruitment-signout" onClick={signOut} type="button">
          <LogOut size={15} /> Sign out
        </button>
      </header>

      <div className="recruitment-content">
        <div className="recruitment-eyebrow">
          <ShieldCheck size={14} /> AUTHORIZED RECRUITMENT WORKSPACE
        </div>

        <div className="recruitment-heading">
          <div>
            <h1>Recruitment <span>operations.</span></h1>
            <p>
              Manage job openings, candidate records, AI-assisted screening,
              and human application reviews.
            </p>
          </div>

          {allowed && (
            <button
              className="recruitment-secondary-button"
              onClick={() => void loadWorkspace(true)}
              disabled={refreshing}
              type="button"
            >
              <RefreshCw
                size={15}
                className={refreshing ? "recruitment-spin" : ""}
              />
              Refresh
            </button>
          )}
        </div>

        {error && (
          <div className="recruitment-alert" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {notice && (
          <div className="recruitment-notice" role="status">
            {notice}
          </div>
        )}

        {!allowed ? (
          <section className="recruitment-panel recruitment-denied">
            <ShieldCheck size={32} />
            <h2>Recruiter access required</h2>
            <p>
              Sign in with an authorized RECRUITER, HR, or ADMIN account to
              access job postings, candidate records, and applications.
            </p>
            <button
              className="recruitment-primary-button"
              onClick={() => router.push("/employees/me")}
              type="button"
            >
              Return to employee profile
            </button>
          </section>
        ) : (
          <>
            <section className="recruitment-metrics">
              <MetricCard
                icon={<BriefcaseBusiness size={19} />}
                label="Open positions"
                value={jobs.filter((job) => job.status?.toLowerCase() === "open").length}
                note={`${jobs.length} total job records`}
              />
              <MetricCard
                icon={<Users size={19} />}
                label="Candidates"
                value={candidates.length}
                note="Registered candidate records"
              />
              <MetricCard
                icon={<FileCheck2 size={19} />}
                label="Applications"
                value={applications.length}
                note={`${pendingReviews} pending human reviews`}
              />
            </section>

            <section className="recruitment-panel">
              <div className="recruitment-tabs" role="tablist">
                <TabButton
                  active={activeTab === "jobs"}
                  onClick={() => setActiveTab("jobs")}
                  icon={<BriefcaseBusiness size={16} />}
                >
                  Job openings
                </TabButton>
                <TabButton
                  active={activeTab === "candidates"}
                  onClick={() => setActiveTab("candidates")}
                  icon={<Users size={16} />}
                >
                  Candidates
                </TabButton>
                <TabButton
                  active={activeTab === "applications"}
                  onClick={() => setActiveTab("applications")}
                  icon={<FileCheck2 size={16} />}
                >
                  Applications
                </TabButton>
              </div>

              {activeTab === "jobs" && (
                <div className="recruitment-section">
                  <SectionHeader
                    title="Job openings"
                    description="Create and manage approved recruitment requisitions."
                    buttonLabel={showJobForm ? "Close form" : "Create job"}
                    onClick={() => setShowJobForm((value) => !value)}
                  />

                  {showJobForm && (
                    <form
                      className="recruitment-form"
                      onSubmit={handleCreateJob}
                    >
                      <div className="recruitment-form-grid">
                        <FormField label="Job code">
                          <input
                            className={inputClassName}
                            value={jobForm.job_code}
                            onChange={(event) =>
                              setJobForm({
                                ...jobForm,
                                job_code: event.target.value,
                              })
                            }
                            placeholder="JOB-2026-001"
                            required
                          />
                        </FormField>
                        <FormField label="Job title">
                          <input
                            className={inputClassName}
                            value={jobForm.title}
                            onChange={(event) =>
                              setJobForm({
                                ...jobForm,
                                title: event.target.value,
                              })
                            }
                            placeholder="AI Engineer"
                            required
                          />
                        </FormField>
                        <FormField label="Department ID">
                          <input
                            className={inputClassName}
                            type="number"
                            min="1"
                            value={jobForm.department_id}
                            onChange={(event) =>
                              setJobForm({
                                ...jobForm,
                                department_id: event.target.value,
                              })
                            }
                            placeholder="e.g. 12"
                            required
                          />
                        </FormField>
                        <FormField label="Minimum experience (years)">
                          <input
                            className={inputClassName}
                            type="number"
                            min="0"
                            value={jobForm.minimum_experience_years}
                            onChange={(event) =>
                              setJobForm({
                                ...jobForm,
                                minimum_experience_years: event.target.value,
                              })
                            }
                            required
                          />
                        </FormField>
                        <FormField label="Required skills">
                          <input
                            className={inputClassName}
                            value={jobForm.required_skills}
                            onChange={(event) =>
                              setJobForm({
                                ...jobForm,
                                required_skills: event.target.value,
                              })
                            }
                            placeholder="Python, SQL, FastAPI"
                            required
                          />
                        </FormField>
                        <FormField label="Preferred skills">
                          <input
                            className={inputClassName}
                            value={jobForm.preferred_skills}
                            onChange={(event) =>
                              setJobForm({
                                ...jobForm,
                                preferred_skills: event.target.value,
                              })
                            }
                            placeholder="Docker, AWS"
                          />
                        </FormField>
                      </div>
                      <FormField label="Job description">
                        <textarea
                          className={inputClassName}
                          value={jobForm.description}
                          onChange={(event) =>
                            setJobForm({
                              ...jobForm,
                              description: event.target.value,
                            })
                          }
                          rows={4}
                          placeholder="Describe responsibilities and role requirements..."
                          required
                        />
                      </FormField>
                      <button
                        className="recruitment-primary-button"
                        type="submit"
                        disabled={submitting}
                      >
                        {submitting ? (
                          <LoaderCircle
                            size={16}
                            className="recruitment-spin"
                          />
                        ) : (
                          <Plus size={16} />
                        )}
                        Publish job opening
                      </button>
                    </form>
                  )}

                  {jobs.length === 0 ? (
                    <EmptyState
                      title="No job openings yet"
                      description="Create a job requisition to start the recruitment workflow."
                    />
                  ) : (
                    <div className="recruitment-record-list">
                      {jobs.map((job) => (
                        <article className="recruitment-record" key={job.id}>
                          <div className="recruitment-record-icon">
                            <BriefcaseBusiness size={18} />
                          </div>
                          <div className="recruitment-record-main">
                            <div className="recruitment-record-title">
                              <h3>{job.title}</h3>
                              <StatusPill value={job.status} />
                            </div>
                            <p>
                              {job.job_code} · Department {job.department_id} ·
                              {" "}{job.minimum_experience_years} years minimum
                            </p>
                            <p className="recruitment-muted">
                              Required: {job.required_skills}
                            </p>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "candidates" && (
                <div className="recruitment-section">
                  <SectionHeader
                    title="Candidate records"
                    description="Register candidate details and resume text for screening."
                    buttonLabel={
                      showCandidateForm ? "Close form" : "Add candidate"
                    }
                    onClick={() =>
                      setShowCandidateForm((value) => !value)
                    }
                  />

                  {showCandidateForm && (
                    <form
                      className="recruitment-form"
                      onSubmit={handleCreateCandidate}
                    >
                      <div className="recruitment-form-grid">
                        <FormField label="Candidate code">
                          <input
                            className={inputClassName}
                            value={candidateForm.candidate_code}
                            onChange={(event) =>
                              setCandidateForm({
                                ...candidateForm,
                                candidate_code: event.target.value,
                              })
                            }
                            placeholder="CAN-2026-001"
                            required
                          />
                        </FormField>
                        <FormField label="Full name">
                          <input
                            className={inputClassName}
                            value={candidateForm.full_name}
                            onChange={(event) =>
                              setCandidateForm({
                                ...candidateForm,
                                full_name: event.target.value,
                              })
                            }
                            required
                          />
                        </FormField>
                        <FormField label="Email address">
                          <input
                            className={inputClassName}
                            type="email"
                            value={candidateForm.email}
                            onChange={(event) =>
                              setCandidateForm({
                                ...candidateForm,
                                email: event.target.value,
                              })
                            }
                            required
                          />
                        </FormField>
                        <FormField label="Phone">
                          <input
                            className={inputClassName}
                            value={candidateForm.phone}
                            onChange={(event) =>
                              setCandidateForm({
                                ...candidateForm,
                                phone: event.target.value,
                              })
                            }
                          />
                        </FormField>
                        <FormField label="Location">
                          <input
                            className={inputClassName}
                            value={candidateForm.location}
                            onChange={(event) =>
                              setCandidateForm({
                                ...candidateForm,
                                location: event.target.value,
                              })
                            }
                          />
                        </FormField>
                        <FormField label="Resume filename (optional)">
                          <input
                            className={inputClassName}
                            value={candidateForm.resume_filename}
                            onChange={(event) =>
                              setCandidateForm({
                                ...candidateForm,
                                resume_filename: event.target.value,
                              })
                            }
                            placeholder="candidate_resume.pdf"
                          />
                        </FormField>
                      </div>
                      <FormField label="Resume text">
                        <textarea
                          className={inputClassName}
                          value={candidateForm.resume_text}
                          onChange={(event) =>
                            setCandidateForm({
                              ...candidateForm,
                              resume_text: event.target.value,
                            })
                          }
                          rows={6}
                          placeholder="Paste the candidate's resume text here. Only provide information relevant to the role."
                        />
                      </FormField>
                      <p className="recruitment-helper">
                        This form stores resume text. It does not upload or
                        parse a PDF file.
                      </p>
                      <button
                        className="recruitment-primary-button"
                        type="submit"
                        disabled={submitting}
                      >
                        {submitting ? (
                          <LoaderCircle
                            size={16}
                            className="recruitment-spin"
                          />
                        ) : (
                          <Plus size={16} />
                        )}
                        Register candidate
                      </button>
                    </form>
                  )}

                  {candidates.length === 0 ? (
                    <EmptyState
                      title="No candidates registered"
                      description="Add a candidate before creating an application."
                    />
                  ) : (
                    <div className="recruitment-record-list">
                      {candidates.map((candidate) => (
                        <article
                          className="recruitment-record"
                          key={candidate.id}
                        >
                          <div className="recruitment-avatar">
                            {candidate.full_name
                              .split(/\s+/)
                              .map((part) => part[0])
                              .slice(0, 2)
                              .join("")
                              .toUpperCase()}
                          </div>
                          <div className="recruitment-record-main">
                            <h3>{candidate.full_name}</h3>
                            <p>
                              {candidate.candidate_code} · {candidate.email}
                            </p>
                            <p className="recruitment-muted">
                              {candidate.location || "Location not provided"}
                              {candidate.resume_filename
                                ? ` · ${candidate.resume_filename}`
                                : ""}
                            </p>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "applications" && (
                <div className="recruitment-section">
                  <SectionHeader
                    title="Applications and reviews"
                    description="Review AI-assisted screening with human oversight."
                    buttonLabel={
                      showApplicationForm ? "Close form" : "Create application"
                    }
                    onClick={() => setShowApplicationForm((value) => !value)}
                  />

                  {showApplicationForm && (
                    <form
                      className="recruitment-form"
                      onSubmit={handleCreateApplication}
                    >
                      <div className="recruitment-form-grid">
                        <FormField label="Job opening">
                          <select
                            className={inputClassName}
                            value={applicationForm.job_id}
                            onChange={(event) =>
                              setApplicationForm({
                                ...applicationForm,
                                job_id: event.target.value,
                              })
                            }
                            required
                          >
                            <option value="">Select a job</option>
                            {jobs.map((job) => (
                              <option key={job.id} value={job.id}>
                                {job.title} ({job.job_code})
                              </option>
                            ))}
                          </select>
                        </FormField>

                        <FormField label="Candidate">
                          <select
                            className={inputClassName}
                            value={applicationForm.candidate_id}
                            onChange={(event) =>
                              setApplicationForm({
                                ...applicationForm,
                                candidate_id: event.target.value,
                              })
                            }
                            required
                          >
                            <option value="">Select a candidate</option>
                            {candidates.map((candidate) => (
                              <option key={candidate.id} value={candidate.id}>
                                {candidate.full_name} ({candidate.candidate_code})
                              </option>
                            ))}
                          </select>
                        </FormField>
                      </div>

                      <p className="recruitment-helper">
                        Screening results are advisory and require human review.
                      </p>

                      <button
                        className="recruitment-primary-button"
                        type="submit"
                        disabled={
                          submitting || jobs.length === 0 || candidates.length === 0
                        }
                      >
                        {submitting ? (
                          <LoaderCircle size={16} className="recruitment-spin" />
                        ) : (
                          <Plus size={16} />
                        )}
                        Create and screen application
                      </button>
                    </form>
                  )}

                  {applications.length === 0 ? (
                    <EmptyState
                      title="No applications yet"
                      description="Register a candidate and create an application to view screening results."
                    />
                  ) : (
                    <div className="recruitment-record-list">
                      {applications.map((application) => {
                        const reviewStatus =
                          application.human_review_status || "Pending";
                        const finalized = ["APPROVED", "REJECTED"].includes(
                          reviewStatus.toUpperCase()
                        );
                        const review = reviewForms[application.id] ?? {
                          review_status: "Review Required",
                          review_notes: "",
                        };
                        const matchedSkills = toSkillList(application.matched_skills);
                        const missingSkills = toSkillList(application.missing_skills);

                        return (
                          <article
                            className="recruitment-application"
                            key={application.id}
                          >
                            <div className="recruitment-application-heading">
                              <div>
                                <span className="recruitment-small-label">
                                  APPLICATION #{application.id}
                                </span>
                                <h3>
                                  {candidateName(candidates, application.candidate_id)}
                                </h3>
                                <p className="recruitment-muted">
                                  {jobTitle(jobs, application.job_id)}
                                </p>
                              </div>
                              <div className="recruitment-status-stack">
                                <StatusPill value={application.application_status} />
                                <StatusPill value={reviewStatus} />
                              </div>
                            </div>

                            <div className="recruitment-fit">
                              <div>
                                <span className="recruitment-small-label">AI FIT SCORE</span>
                                <strong>
                                  {typeof application.ai_fit_score === "number"
                                    ? `${application.ai_fit_score.toFixed(1)}%`
                                    : "Not available"}
                                </strong>
                              </div>
                              <div>
                                <span className="recruitment-small-label">AI RECOMMENDATION</span>
                                <strong>
                                  {application.ai_recommendation ||
                                    "Human assessment required"}
                                </strong>
                              </div>
                            </div>

                            <details className="recruitment-screening-details">
                              <summary>View AI screening details</summary>
                              {application.ai_summary && (
                                <p className="recruitment-summary">
                                  {application.ai_summary}
                                </p>
                              )}
                              <div className="recruitment-skills-grid">
                                <div>
                                  <span className="recruitment-small-label">MATCHED SKILLS</span>
                                  <div className="recruitment-chip-list">
                                    {matchedSkills.length > 0 ? (
                                      matchedSkills.map((skill) => (
                                        <span className="recruitment-chip" key={skill}>
                                          {skill}
                                        </span>
                                      ))
                                    ) : (
                                      <span className="recruitment-muted">None recorded</span>
                                    )}
                                  </div>
                                </div>
                                <div>
                                  <span className="recruitment-small-label">MISSING SKILLS</span>
                                  <div className="recruitment-chip-list">
                                    {missingSkills.length > 0 ? (
                                      missingSkills.map((skill) => (
                                        <span
                                          className="recruitment-chip recruitment-chip-muted"
                                          key={skill}
                                        >
                                          {skill}
                                        </span>
                                      ))
                                    ) : (
                                      <span className="recruitment-muted">None recorded</span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </details>

                            {finalized ? (
                              <div className="recruitment-review-complete">
                                <ShieldCheck size={16} />
                                <span>
                                  {`Finalized by ${application.reviewed_by || "authorized reviewer"}`}
                                  {application.review_notes ? ` — ${application.review_notes}` : ""}
                                </span>
                              </div>
                            ) : (
                              <form
                                className="recruitment-review-form"
                                onSubmit={(event) => void handleReview(event, application.id)}
                              >
                                <div className="recruitment-review-title">
                                  <ShieldCheck size={17} />
                                  Human review
                                </div>
                                <div className="recruitment-form-grid">
                                  <FormField label="Review decision">
                                    <select
                                      className={inputClassName}
                                      value={review.review_status}
                                      onChange={(event) =>
                                        setReviewForms((current) => ({
                                          ...current,
                                          [application.id]: {
                                            ...review,
                                            review_status: event.target.value,
                                          },
                                        }))
                                      }
                                    >
                                      <option value="Review Required">Review Required</option>
                                      <option value="Approved">Approve</option>
                                      <option value="Rejected">Reject</option>
                                    </select>
                                  </FormField>
                                  <FormField label="Review notes">
                                    <input
                                      className={inputClassName}
                                      value={review.review_notes}
                                      onChange={(event) =>
                                        setReviewForms((current) => ({
                                          ...current,
                                          [application.id]: {
                                            ...review,
                                            review_notes: event.target.value,
                                          },
                                        }))
                                      }
                                      placeholder="Record your assessment"
                                    />
                                  </FormField>
                                </div>
                                <button
                                  className="recruitment-primary-button"
                                  type="submit"
                                  disabled={submitting}
                                >
                                  {submitting ? (
                                    <LoaderCircle size={16} className="recruitment-spin" />
                                  ) : (
                                    <ShieldCheck size={16} />
                                  )}
                                  Save human review
                                </button>
                              </form>
                            )}

                            {canConfirmHire &&
                              application.id === 2 &&
                              reviewStatus.toUpperCase() === "APPROVED" &&
                              application.application_status.toUpperCase() !== "HIRED" && (
                                <section className="recruitment-review-form">
                                  <div className="recruitment-review-title">
                                    <ShieldCheck size={17} />
                                    HR hiring confirmation
                                  </div>
                                  <p className="recruitment-helper">
                                    Approval is not a hire. Enter employment details confirmed by HR. Submitting creates the employee record and onboarding tasks/documents.
                                  </p>

                                  {hiringApplicationId !== application.id ? (
                                    <button
                                      className="recruitment-primary-button"
                                      type="button"
                                      onClick={() => {
                                        setHiringApplicationId(application.id);
                                        setHiringForms((current) => ({
                                          ...current,
                                          [application.id]: current[application.id] ?? createHiringFormState(),
                                        }));
                                        setError("");
                                      }}
                                    >
                                      <ShieldCheck size={16} />
                                      Confirm hire and start onboarding
                                    </button>
                                  ) : (
                                    <form
                                      className="recruitment-form"
                                      onSubmit={(event) => void handleConfirmHire(event, application.id)}
                                    >
                                      {(() => {
                                        const form = hiringForms[application.id] ?? createHiringFormState();
                                        const updateHiringField = (
                                          field: keyof HiringFormState,
                                          value: string,
                                        ) => setHiringForms((current) => ({
                                          ...current,
                                          [application.id]: {
                                            ...(current[application.id] ?? createHiringFormState()),
                                            [field]: value,
                                          },
                                        }));
                                        return (
                                          <>
                                            <div className="recruitment-form-grid">
                                              <FormField label="Gender (HR-confirmed)">
                                                <input className={inputClassName} value={form.gender} onChange={(event) => updateHiringField("gender", event.target.value)} required maxLength={20} />
                                              </FormField>
                                              <FormField label="Age">
                                                <input className={inputClassName} type="number" min="18" max="100" value={form.age} onChange={(event) => updateHiringField("age", event.target.value)} required />
                                              </FormField>
                                              <FormField label="Job level">
                                                <input className={inputClassName} value={form.job_level} onChange={(event) => updateHiringField("job_level", event.target.value)} placeholder="e.g. L1, Junior" required maxLength={50} />
                                              </FormField>
                                              <FormField label="Work location">
                                                <input className={inputClassName} value={form.work_location} onChange={(event) => updateHiringField("work_location", event.target.value)} placeholder="e.g. Bengaluru" required maxLength={100} />
                                              </FormField>
                                              <FormField label="Joining date">
                                                <input className={inputClassName} type="date" value={form.joining_date} onChange={(event) => updateHiringField("joining_date", event.target.value)} required />
                                              </FormField>
                                              <FormField label="Annual base salary (INR)">
                                                <input className={inputClassName} type="number" min="1" step="1" value={form.annual_base_salary_inr} onChange={(event) => updateHiringField("annual_base_salary_inr", event.target.value)} required />
                                              </FormField>
                                              <FormField label="Education">
                                                <input className={inputClassName} value={form.education} onChange={(event) => updateHiringField("education", event.target.value)} required maxLength={100} />
                                              </FormField>
                                              <FormField label="Marital status">
                                                <input className={inputClassName} value={form.marital_status} onChange={(event) => updateHiringField("marital_status", event.target.value)} required maxLength={30} />
                                              </FormField>
                                              <FormField label="Tenure at period start (years)">
                                                <input className={inputClassName} type="number" min="0" max="60" step="0.1" value={form.tenure_years_at_period_start} onChange={(event) => updateHiringField("tenure_years_at_period_start", event.target.value)} />
                                              </FormField>
                                              <FormField label="Manager employee ID (optional)">
                                                <input className={inputClassName} value={form.manager_id} onChange={(event) => updateHiringField("manager_id", event.target.value)} placeholder="e.g. EMP0012" maxLength={20} />
                                              </FormField>
                                            </div>
                                            <div className="recruitment-form-actions">
                                              <button className="recruitment-primary-button" type="submit" disabled={submitting}>
                                                {submitting ? <LoaderCircle size={16} className="recruitment-spin" /> : <ShieldCheck size={16} />}
                                                Confirm hire
                                              </button>
                                              <button className="recruitment-secondary-button" type="button" disabled={submitting} onClick={() => setHiringApplicationId(null)}>
                                                Cancel
                                              </button>
                                            </div>
                                          </>
                                        );
                                      })()}
                                    </form>
                                  )}
                                </section>
                              )}

                            <p className="recruitment-helper">
                              AI scores and recommendations are decision support only.
                              Review the candidate&apos;s qualifications and job requirements
                              before making a hiring decision.
                            </p>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </section>

            <footer className="recruitment-footer">
              <ShieldCheck size={14} />
              Signed in as {user.email} · {user.role}
              <span>AI-assisted screening · Human-led hiring decisions</span>
            </footer>
          </>
        )}
      </div>
    </main>
  );
}

function MetricCard({
  icon,
  label,
  value,
  note,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  note: string;
}) {
  return (
    <article className="recruitment-metric">
      <div className="recruitment-metric-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={`recruitment-tab ${active ? "active" : ""}`}
      onClick={onClick}
    >
      {icon}
      {children}
    </button>
  );
}

function SectionHeader({
  title,
  description,
  buttonLabel,
  onClick,
}: {
  title: string;
  description: string;
  buttonLabel: string;
  onClick: () => void;
}) {
  return (
    <div className="recruitment-section-header">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <button
        className="recruitment-primary-button"
        type="button"
        onClick={onClick}
      >
        <Plus size={15} />
        {buttonLabel}
      </button>
    </div>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="recruitment-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="recruitment-empty">
      <BriefcaseBusiness size={25} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase().replace(/[\s_-]+/g, "-");
  const tone = ["approved", "open", "strong-match"].includes(normalized)
    ? "positive"
    : ["rejected", "closed", "needs-review"].includes(normalized)
      ? "negative"
      : "neutral";

  return (
    <span className={`recruitment-status ${tone}`}>
      {value.replace(/_/g, " ")}
    </span>
  );
}

function candidateName(candidates: Candidate[], candidateId: number) {
  return (
    candidates.find((candidate) => candidate.id === candidateId)?.full_name ??
    `Candidate #${candidateId}`
  );
}

function jobTitle(jobs: Job[], jobId: number) {
  return (
    jobs.find((job) => job.id === jobId)?.title ?? `Job #${jobId}`
  );
}
