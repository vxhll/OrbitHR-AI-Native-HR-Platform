
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  Users,
  TrendingDown,
  MessageSquareText,
  AlertCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

const BRONZE = "#c79b5a";
const COLORS = ["#c79b5a", "#8c7656", "#625d51", "#a7a092", "#70533b"];

type User = {
  email: string;
  role: string;
  is_active: boolean;
};

type Breakdown = {
  exit_type: string;
  count: number;
};

type ReasonBreakdown = {
  exit_reason: string;
  count: number;
};

type DepartmentBreakdown = {
  department_id: number;
  department_name: string;
  count: number;
};

type MonthlyExit = {
  month: string;
  count: number;
};

type ExitAnalytics = {
  total_recorded_exits: number;
  exit_type_breakdown: Breakdown[];
  exit_reason_breakdown: ReasonBreakdown[];
  department_exit_breakdown: DepartmentBreakdown[];
  monthly_exit_trends: MonthlyExit[];
  exit_interviews: {
    total_interviews: number;
    average_satisfaction: number | null;
    recommendation_responses: number;
    recommendation_yes: number;
    recommendation_percentage: number | null;
  };
};

export default function ExitAnalyticsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [data, setData] = useState<ExitAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const apiRequest = useCallback(async (path: string) => {
    const token = sessionStorage.getItem("orbithr_access_token");

    if (!token) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const response = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    const body = await response.json().catch(() => null);

    if (response.status === 401) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    if (response.status === 403) {
      throw new Error("HR or Admin access is required for exit analytics.");
    }

    if (!response.ok) {
      throw new Error(
        typeof body?.detail === "string"
          ? body.detail
          : `Request failed (HTTP ${response.status}).`,
      );
    }

    return body;
  }, []);

  const loadAnalytics = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);

      setError("");

      try {
        const token = sessionStorage.getItem("orbithr_access_token");

        if (!token) {
          router.replace("/login");
          return;
        }

        const currentUser: User = await apiRequest("/api/auth/me");

        if (!currentUser.is_active) {
          sessionStorage.removeItem("orbithr_access_token");
          sessionStorage.removeItem("orbithr_user");
          router.replace("/login");
          return;
        }

        if (!["HR", "ADMIN"].includes(currentUser.role.toUpperCase())) {
          setUser(currentUser);
          setError("Exit analytics is restricted to HR and Admin users.");
          return;
        }

        setUser(currentUser);

        const result = (await apiRequest(
          "/api/analytics/exits",
        )) as ExitAnalytics;

        setData(result);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unable to load exit analytics.";

        if (message.includes("session has expired")) {
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
      void loadAnalytics();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadAnalytics]);

  if (loading) {
    return (
      <main className="recruitment-shell">
        <div className="recruitment-loading">
          <RefreshCw className="recruitment-spin" size={25} />
          <p>Verifying access and loading exit analytics...</p>
        </div>
      </main>
    );
  }

  const interviews = data?.exit_interviews;

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
            <TrendingDown size={19} />
          </span>
          <span>
            ORBIT HR <small>/ EXIT INTELLIGENCE</small>
          </span>
        </div>

        <button
          className="recruitment-secondary-button"
          onClick={() => void loadAnalytics(true)}
          disabled={refreshing}
          type="button"
        >
          <RefreshCw
            size={15}
            className={refreshing ? "recruitment-spin" : ""}
          />
          Refresh
        </button>
      </header>

      <div className="recruitment-content">
        <div className="recruitment-eyebrow">
          <ShieldCheck size={14} /> AUTHORIZED HR WORKSPACE
        </div>

        <div className="recruitment-heading">
          <div>
            <h1>
              Exit <span>analytics.</span>
            </h1>
            <p>
              Understand employee departures, exit reasons, departmental
              patterns, and feedback from exit interviews.
            </p>
          </div>
        </div>

        {error && (
          <div className="recruitment-alert" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {!user ||
        !["HR", "ADMIN"].includes(user.role.toUpperCase()) ? (
          <section className="recruitment-panel recruitment-denied">
            <ShieldCheck size={32} />
            <h2>Authorized access required</h2>
            <p>
              Sign in with an active HR or Admin account to access exit
              analytics.
            </p>
            <button
              className="recruitment-primary-button"
              onClick={() => router.push("/")}
              type="button"
            >
              Return to dashboard
            </button>
          </section>
        ) : data ? (
          <>
            <section className="recruitment-metrics">
              <Metric
                label="Recorded exits"
                value={data.total_recorded_exits}
                note="Exit records in the system"
                icon={<Users size={19} />}
              />
              <Metric
                label="Exit interviews"
                value={interviews?.total_interviews ?? 0}
                note="Recorded interview responses"
                icon={<MessageSquareText size={19} />}
              />
              <Metric
                label="Average satisfaction"
                value={
                  interviews?.average_satisfaction == null
                    ? "N/A"
                    : `${interviews.average_satisfaction.toFixed(1)}/10`
                }
                note="Among recorded satisfaction scores"
                icon={<TrendingDown size={19} />}
              />
            </section>

            <section className="exit-grid">
              <ChartPanel
                title="Monthly exit trend"
                description="Recorded exits grouped by month"
              >
                {data.monthly_exit_trends.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.monthly_exit_trends}
                      margin={{ top: 10, right: 10, left: -15, bottom: 5 }}
                    >
                      <CartesianGrid
                        stroke="#292824"
                        strokeDasharray="3 3"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="month"
                        tick={{ fill: "#aaa69b", fontSize: 10 }}
                        axisLine={{ stroke: "#39372f" }}
                        tickLine={false}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: "#aaa69b", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#171714",
                          border: "1px solid #39372f",
                          borderRadius: 8,
                          color: "#f3f0e8",
                        }}
                      />
                      <Bar
                        dataKey="count"
                        name="Exits"
                        fill={BRONZE}
                        radius={[5, 5, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyChart message="No monthly exit records available." />
                )}
              </ChartPanel>

              <ChartPanel
                title="Exit type breakdown"
                description="Distribution by recorded exit type"
              >
                {data.exit_type_breakdown.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.exit_type_breakdown}
                        dataKey="count"
                        nameKey="exit_type"
                        cx="50%"
                        cy="48%"
                        innerRadius={58}
                        outerRadius={88}
                        paddingAngle={3}
                      >
                        {data.exit_type_breakdown.map((item, index) => (
                          <Cell
                            key={item.exit_type}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "#171714",
                          border: "1px solid #39372f",
                          borderRadius: 8,
                          color: "#f3f0e8",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyChart message="No exit type data available." />
                )}
                <div className="exit-legend">
                  {data.exit_type_breakdown.map((item, index) => (
                    <div key={item.exit_type}>
                      <span>
                        <i
                          style={{
                            background: COLORS[index % COLORS.length],
                          }}
                        />
                        {item.exit_type}
                      </span>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              </ChartPanel>

              <ChartPanel
                title="Reasons for leaving"
                description="Recorded reasons across all exits"
              >
                {data.exit_reason_breakdown.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.exit_reason_breakdown}
                      layout="vertical"
                      margin={{ top: 5, right: 15, left: 8, bottom: 5 }}
                    >
                      <CartesianGrid
                        stroke="#292824"
                        strokeDasharray="3 3"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tick={{ fill: "#aaa69b", fontSize: 10 }}
                        axisLine={{ stroke: "#39372f" }}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="exit_reason"
                        width={115}
                        tick={{ fill: "#c4bcae", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#171714",
                          border: "1px solid #39372f",
                          borderRadius: 8,
                          color: "#f3f0e8",
                        }}
                      />
                      <Bar
                        dataKey="count"
                        name="Exits"
                        fill={BRONZE}
                        radius={[0, 5, 5, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyChart message="No exit reasons available." />
                )}
              </ChartPanel>

              <ChartPanel
                title="Department exits"
                description="Recorded exits by department"
              >
                {data.department_exit_breakdown.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.department_exit_breakdown}
                      layout="vertical"
                      margin={{ top: 5, right: 15, left: 8, bottom: 5 }}
                    >
                      <CartesianGrid
                        stroke="#292824"
                        strokeDasharray="3 3"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tick={{ fill: "#aaa69b", fontSize: 10 }}
                        axisLine={{ stroke: "#39372f" }}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="department_name"
                        width={115}
                        tick={{ fill: "#c4bcae", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#171714",
                          border: "1px solid #39372f",
                          borderRadius: 8,
                          color: "#f3f0e8",
                        }}
                      />
                      <Bar
                        dataKey="count"
                        name="Exits"
                        fill={BRONZE}
                        radius={[0, 5, 5, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyChart message="No department exit data available." />
                )}
              </ChartPanel>
            </section>

            <section className="exit-interview-panel">
              <div>
                <span className="recruitment-small-label">
                  EXIT INTERVIEW INSIGHTS
                </span>
                <h2>Employee feedback</h2>
                <p>
                  Summaries based on the exit interview records currently
                  available in OrbitHR.
                </p>
              </div>

              <div className="exit-interview-stats">
                <div>
                  <span>Would recommend company</span>
                  <strong>
                    {interviews?.recommendation_percentage == null
                      ? "N/A"
                      : `${interviews.recommendation_percentage.toFixed(1)}%`}
                  </strong>
                  <small>
                    {interviews?.recommendation_yes ?? 0} yes out of{" "}
                    {interviews?.recommendation_responses ?? 0} responses
                  </small>
                </div>
                <div>
                  <span>Average satisfaction</span>
                  <strong>
                    {interviews?.average_satisfaction == null
                      ? "N/A"
                      : `${interviews.average_satisfaction.toFixed(1)} / 10`}
                  </strong>
                  <small>
                    Based on recorded satisfaction scores
                  </small>
                </div>
              </div>
            </section>

            <footer className="recruitment-footer">
              <ShieldCheck size={14} />
              Signed in as {user.email} · {user.role}
              <span>HR analytics · Source: live API data</span>
            </footer>
          </>
        ) : null}
      </div>
    </main>
  );
}

function Metric({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: string | number;
  note: string;
  icon: React.ReactNode;
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

function ChartPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="recruitment-panel exit-chart-panel">
      <div className="exit-chart-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      <div className="exit-chart-area">{children}</div>
    </section>
  );
}

function EmptyChart({ message }: { message: string }) {
  return <div className="exit-empty-chart">{message}</div>;
}
