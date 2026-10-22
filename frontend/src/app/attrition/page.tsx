"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  LoaderCircle,
  Search,
  ShieldAlert,
  Sparkles,
  UserRound,
} from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type Driver = {
  feature: string;
  value: number | string;
  contribution_log_odds: number;
  direction: "increases" | "decreases" | "neutral";
};

type FeatureValues = Record<string, number | string>;

type PredictionResult = {
  employee_id: string;
  prediction_date: string;
  prediction: {
    attrition_probability_percent: number;
    risk_level: "Low" | "Medium" | "High";
    predicted_attrition: boolean;
    classification_threshold: number;
    outcome_horizon_days: number;
  };
  model: {
    name: string;
    version: string;
  };
  data_source: string;
  research_notice: string;
  features: FeatureValues;
  explanation: {
    method: string;
    baseline_log_odds: number;
    reconstructed_log_odds: number;
    reference: string;
    top_positive_drivers: Driver[];
    top_negative_drivers: Driver[];
    contributions: Driver[];
  };
};

function formatFeatureName(name: string) {
  return name
    .replace(/_90d/g, " (90d)")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value: number | string) {
  if (typeof value === "number") {
    return new Intl.NumberFormat("en-IN", {
      maximumFractionDigits: 3,
    }).format(value);
  }
  return value;
}

function formatCurrency(value: number | string) {
  if (typeof value !== "number") return String(value);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function getRiskClass(risk: string) {
  return risk.toLowerCase();
}

function DriverCard({
  title,
  description,
  drivers,
  positive,
}: {
  title: string;
  description: string;
  drivers: Driver[];
  positive: boolean;
}) {
  return (
    <article className="attrition-panel driver-panel">
      <div className="attrition-panel-heading">
        <div className={`driver-heading-icon ${positive ? "driver-up" : "driver-down"}`}>
          {positive ? <ArrowUpRight size={19} /> : <ArrowDownRight size={19} />}
        </div>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>

      {drivers.length ? (
        <div className="driver-list">
          {drivers.map((driver, index) => {
            const magnitude = Math.min(
              100,
              Math.max(5, Math.abs(driver.contribution_log_odds) * 220),
            );

            return (
              <div className="driver-row" key={`${driver.feature}-${index}`}>
                <div className="driver-row-top">
                  <span>{formatFeatureName(driver.feature)}</span>
                  <strong>
                    {driver.contribution_log_odds > 0 ? "+" : ""}
                    {driver.contribution_log_odds.toFixed(4)}
                  </strong>
                </div>
                <div className="driver-bar-track">
                  <div
                    className={`driver-bar ${positive ? "driver-bar-positive" : "driver-bar-negative"}`}
                    style={{ width: `${magnitude}%` }}
                  />
                </div>
                <div className="driver-row-meta">
                  <span>Observed value: {formatValue(driver.value)}</span>
                  <span>{driver.direction}</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="attrition-muted">No drivers available.</p>
      )}
    </article>
  );
}

export default function AttritionPage() {
  const [employeeId, setEmployeeId] = useState("EMP0001");
  const [predictionDate, setPredictionDate] = useState("2025-12-01");
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runPrediction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const id = employeeId.trim().toUpperCase();

      if (!id) {
        throw new Error("Enter a synthetic employee ID.");
      }

      const params = new URLSearchParams({
        prediction_date: predictionDate,
      });

      const response = await fetch(
        `${API_BASE}/api/analytics/attrition-predict-v3/${encodeURIComponent(id)}?${params.toString()}`,
        { cache: "no-store" },
      );

      const body = await response.json().catch(() => null);

      if (!response.ok) {
        const detail =
          typeof body?.detail === "string"
            ? body.detail
            : `Request failed with HTTP ${response.status}.`;
        throw new Error(detail);
      }

      setResult(body as PredictionResult);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to generate the prediction.",
      );
    } finally {
      setLoading(false);
    }
  }

  const prediction = result?.prediction;
  const probability = prediction?.attrition_probability_percent ?? 0;
  const features = result?.features;

  return (
    <main className="attrition-shell">
      <header className="attrition-topbar">
        <Link href="/" className="attrition-back">
          <ArrowLeft size={17} />
          <span>Workforce overview</span>
        </Link>
        <div className="attrition-brand">
          <span className="attrition-brand-mark">
            <BrainCircuit size={19} />
          </span>
          <span>ORBIT HR <small>/ AI INTELLIGENCE</small></span>
        </div>
        <span className="attrition-version">EVENT-BASED V3</span>
      </header>

      <div className="attrition-content">
        <div className="attrition-page-heading">
          <div className="attrition-eyebrow">
            <Sparkles size={13} />
            EXPLAINABLE MACHINE LEARNING
          </div>
          <h1>Attrition <span>Intelligence</span></h1>
          <p>
            Inspect a synthetic employee snapshot, its model score, and the
            feature contributions behind the prediction.
          </p>
        </div>

        <div className="research-notice">
          <ShieldAlert size={20} />
          <div>
            <strong>Research prototype — synthetic data only</strong>
            <p>
              This model is not validated for real employees. Its output must
              not independently determine hiring, promotion, compensation,
              termination, or other employment decisions.
            </p>
          </div>
        </div>

        <div className="attrition-layout">
          <aside className="attrition-panel prediction-form-panel">
            <div className="attrition-eyebrow">01 / MODEL INPUT</div>
            <h2>Run a prediction</h2>
            <p className="form-intro">
              Select an employee and a supported historical snapshot date.
            </p>

            <form onSubmit={runPrediction}>
              <label htmlFor="employee-id">
                <UserRound size={15} />
                Synthetic employee ID
              </label>
              <input
                id="employee-id"
                value={employeeId}
                onChange={(event) => setEmployeeId(event.target.value)}
                placeholder="EMP0001"
                required
                autoComplete="off"
              />

              <label htmlFor="prediction-date">
                <CalendarDays size={15} />
                Prediction snapshot date
              </label>
              <input
                id="prediction-date"
                type="date"
                value={predictionDate}
                onChange={(event) => setPredictionDate(event.target.value)}
                min="2025-01-01"
                max="2025-12-01"
                required
              />

              <button className="run-prediction-button" type="submit" disabled={loading}>
                {loading ? (
                  <LoaderCircle className="attrition-spin" size={17} />
                ) : (
                  <Search size={17} />
                )}
                {loading ? "Analyzing snapshot..." : "Generate prediction"}
              </button>
            </form>

            <div className="input-help">
              <CircleAlert size={15} />
              <p>
                Only employee/date combinations present in the v3 snapshot
                dataset are supported. A valid calendar date may still be
                unavailable for a particular employee.
              </p>
            </div>

            <div className="model-info">
              <div className="model-info-row">
                <span>Model</span>
                <strong>Logistic Regression</strong>
              </div>
              <div className="model-info-row">
                <span>Version</span>
                <strong>event-based-v3</strong>
              </div>
              <div className="model-info-row">
                <span>Feature lookback</span>
                <strong>90 days</strong>
              </div>
              <div className="model-info-row">
                <span>Outcome horizon</span>
                <strong>180 days</strong>
              </div>
            </div>
          </aside>

          <section className="attrition-results">
            {error && (
              <div className="attrition-error" role="alert">
                <CircleAlert size={20} />
                <div>
                  <strong>Prediction unavailable</strong>
                  <p>{error}</p>
                  <span>
                    Check the employee ID and supported snapshot date, then
                    try again.
                  </span>
                </div>
              </div>
            )}

            {!result && !error && !loading && (
              <div className="attrition-empty attrition-panel">
                <div className="empty-brain">
                  <BrainCircuit size={34} />
                </div>
                <h2>Ready to analyze</h2>
                <p>
                  Run a prediction to see the model score, risk band, feature
                  values, and strongest score contributions.
                </p>
                <div className="empty-steps">
                  <span>01 <small>Choose snapshot</small></span>
                  <span>02 <small>Generate score</small></span>
                  <span>03 <small>Review explanation</small></span>
                </div>
              </div>
            )}

            {loading && (
              <div className="attrition-empty attrition-panel">
                <LoaderCircle className="attrition-spin" size={30} />
                <h2>Evaluating snapshot</h2>
                <p>Requesting the event-based model prediction.</p>
              </div>
            )}

            {result && prediction && (
              <>
                <div className="attrition-result-heading">
                  <div>
                    <div className="attrition-eyebrow">02 / PREDICTION RESULT</div>
                    <h2>Snapshot analysis</h2>
                    <p>
                      {result.employee_id} <span>·</span> {result.prediction_date}
                    </p>
                  </div>
                  <span className="result-model-badge">
                    <CheckCircle2 size={14} />
                    {result.model.version}
                  </span>
                </div>

                <article className="probability-card">
                  <div className="probability-copy">
                    <span className="probability-label">ATTRITION PROBABILITY</span>
                    <div className="probability-number">
                      {probability.toFixed(2)}<span>%</span>
                    </div>
                    <p>Model-estimated score for the 180-day outcome horizon.</p>
                  </div>

                  <div className="probability-visual">
                    <div
                      className={`risk-ring risk-ring-${getRiskClass(prediction.risk_level)}`}
                      style={{ "--probability": `${Math.max(0, Math.min(100, probability))}%` } as React.CSSProperties}
                    >
                      <div className="risk-ring-inner">
                        <BrainCircuit size={26} />
                      </div>
                    </div>
                    <span className={`risk-pill risk-pill-${getRiskClass(prediction.risk_level)}`}>
                      {prediction.risk_level} risk band
                    </span>
                  </div>

                  <div className="probability-footer">
                    <div>
                      <span>Classification threshold</span>
                      <strong>
                        {(prediction.classification_threshold * 100).toFixed(1)}%
                      </strong>
                    </div>
                    <div>
                      <span>Binary classification</span>
                      <strong>{prediction.predicted_attrition ? "Positive" : "Negative"}</strong>
                    </div>
                    <div>
                      <span>Snapshot source</span>
                      <strong>{result.data_source}</strong>
                    </div>
                  </div>
                </article>

                <div className="explanation-heading">
                  <div className="attrition-eyebrow">03 / EXPLAINABILITY</div>
                  <h2>What influenced the score?</h2>
                  <p>
                    Contributions are measured in transformed log-odds space,
                    not percentage-point changes or causal effects.
                  </p>
                </div>

                <div className="driver-grid">
                  <DriverCard
                    title="Increasing the score"
                    description="Largest positive log-odds contributions"
                    drivers={result.explanation.top_positive_drivers}
                    positive
                  />
                  <DriverCard
                    title="Decreasing the score"
                    description="Largest negative log-odds contributions"
                    drivers={result.explanation.top_negative_drivers}
                    positive={false}
                  />
                </div>

                <article className="attrition-panel feature-panel">
                  <div className="attrition-panel-heading feature-heading">
                    <div>
                      <h3>Snapshot feature values</h3>
                      <p>Input values supplied to the v3 model</p>
                    </div>
                    <span className="feature-count">
                      {Object.keys(features ?? {}).length} FEATURES
                    </span>
                  </div>
                  <div className="feature-grid">
                    {Object.entries(features ?? {}).map(([key, value]) => (
                      <div className="feature-item" key={key}>
                        <span>{formatFeatureName(key)}</span>
                        <strong>
                          {key === "annual_base_salary_inr"
                            ? formatCurrency(value)
                            : formatValue(value)}
                        </strong>
                      </div>
                    ))}
                  </div>
                </article>

                <div className="explanation-footnote">
                  <ShieldAlert size={17} />
                  <div>
                    <strong>Interpret with care</strong>
                    <p>{result.research_notice}</p>
                    <p>{result.explanation.reference}</p>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>

        <footer className="attrition-footer">
          ORBIT HR / PEOPLE INTELLIGENCE
          <span>Human review required · Synthetic research prototype</span>
        </footer>
      </div>
    </main>
  );
}
