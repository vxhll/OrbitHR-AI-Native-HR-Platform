
"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BrainCircuit, LoaderCircle, ShieldCheck } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
        cache: "no-store",
      });

      const body = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : `Login failed (HTTP ${response.status}).`,
        );
      }

      if (typeof body?.access_token !== "string") {
        throw new Error("The server did not return an access token.");
      }

      // Session-only storage: the token is cleared when this tab's session ends.
      sessionStorage.setItem("orbithr_access_token", body.access_token);

      const userResponse = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${body.access_token}` },
        cache: "no-store",
      });

      const user = await userResponse.json().catch(() => null);

      if (!userResponse.ok) {
        sessionStorage.removeItem("orbithr_access_token");
        throw new Error("Login succeeded, but the user session could not be verified.");
      }

      sessionStorage.setItem("orbithr_user", JSON.stringify(user));
      const role = String(user?.role ?? "").toUpperCase();

     if (["RECRUITER", "HR", "ADMIN"].includes(role)) {
       router.push("/recruitment");
     } else {
       router.push("/employees/me");
     }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to sign in.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="attrition-shell">
      <div className="attrition-content" style={{ maxWidth: 520, margin: "10vh auto" }}>
        <div className="attrition-brand" style={{ justifyContent: "center", marginBottom: 36 }}>
          <span className="attrition-brand-mark">
            <BrainCircuit size={21} />
          </span>
          <span>ORBIT HR <small>/ PEOPLE INTELLIGENCE</small></span>
        </div>

        <section className="attrition-panel prediction-form-panel">
          <div className="attrition-eyebrow">
            <ShieldCheck size={14} />
            SECURE EMPLOYEE ACCESS
          </div>

          <h1 style={{ marginTop: 14 }}>Welcome <span>back.</span></h1>
          <p className="form-intro">
            Sign in to access your employee profile and workforce insights.
          </p>

          <form onSubmit={handleSubmit}>
            <label htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              autoComplete="username"
              required
            />

            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              required
            />

            {error && (
              <div className="attrition-error" role="alert">
                <p>{error}</p>
              </div>
            )}

            <button
              className="run-prediction-button"
              type="submit"
              disabled={loading}
              style={{ width: "100%", marginTop: 24 }}
            >
              {loading ? (
                <LoaderCircle className="attrition-spin" size={17} />
              ) : (
                <ArrowRight size={17} />
              )}
              {loading ? "Verifying..." : "Sign in securely"}
            </button>
          </form>

          <p className="input-help" style={{ marginTop: 22 }}>
            Your session token is stored for this browser tab only. Always sign
            out on shared devices.
          </p>
        </section>
      </div>
    </main>
  );
}
