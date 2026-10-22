"use client";

import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  BrainCircuit,
  Building2,
  ChevronDown,
  CircleHelp,
  Command,
  LayoutDashboard,
  LoaderCircle,
  Search,
  Settings,
  ShieldCheck,
  Users,
  Wallet,
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

type Overview = {
  headcount: { total: number; active: number; exited: number };
  attrition: { exited_employees: number; attrition_rate_percent: number };
  workforce: {
    average_age: number;
    average_annual_salary_inr: number;
  };
  workforce_signals: {
    average_attendance_hours: number;
    average_performance_rating: number;
    average_engagement_score: number;
  };
};

type Department = {
  department_id: number;
  headcount: number;
  active_employees: number;
  exited_employees: number;
  attrition_rate_percent: number;
  average_engagement_score: number;
  average_performance_rating: number;
};

type DepartmentResponse = {
  count: number;
  departments: Department[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

const bronze = "#C79B5A";
const chartColors = ["#C79B5A", "#8B7049", "#5E503D", "#D9C19A"];

const departmentNames: Record<number, string> = {
  11: "Customer Support",
  12: "Engineering",
  13: "Finance",
  14: "HR",
  15: "IT",
  16: "Legal",
  17: "Marketing",
  18: "Operations",
  19: "Product",
  20: "Sales",
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 1,
  }).format(value);
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
    notation: value >= 10000000 ? "compact" : "standard",
  }).format(value);
}


function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  accent = false,
}: {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  accent?: boolean;
}) {
  return (
    <article className={`metric-card ${accent ? "metric-card-accent" : ""}`}>
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className="metric-icon">
          <Icon size={18} strokeWidth={1.7} />
        </span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function SectionTitle({
  eyebrow,
  title,
  detail,
}: {
  eyebrow: string;
  title: string;
  detail: string;
}) {
  return (
    <div className="section-title">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
      </div>
      <p>{detail}</p>
    </div>
  );
}

export default function Home() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [departmentData, setDepartmentData] =
    useState<DepartmentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [overviewResponse, departmentsResponse] = await Promise.all([
          fetch(`${API_BASE}/api/analytics/overview`, {
            signal: controller.signal,
            cache: "no-store",
          }),
          fetch(`${API_BASE}/api/analytics/departments`, {
            signal: controller.signal,
            cache: "no-store",
          }),
        ]);

        if (!overviewResponse.ok || !departmentsResponse.ok) {
          throw new Error(
            `API request failed (overview: ${overviewResponse.status}, departments: ${departmentsResponse.status}).`,
          );
        }

        const [overviewJson, departmentsJson] = await Promise.all([
          overviewResponse.json(),
          departmentsResponse.json(),
        ]);

        setOverview(overviewJson);
        setDepartmentData(departmentsJson);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load workforce analytics.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    loadDashboard();

    return () => controller.abort();
  }, []);

  const departments = (departmentData?.departments ?? []).map((item) => ({
    ...item,
    name: departmentNames[item.department_id] ?? `Department ${item.department_id}`,
  }));

  const engagementData = departments.filter(
    (item) => item.average_engagement_score > 0,
  );

  const pieData = overview
    ? [
        { name: "Active", value: overview.headcount.active },
        { name: "Exited", value: overview.headcount.exited },
      ].filter((item) => item.value > 0)
    : [];

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a href="#" className="brand">
          <span className="brand-mark">
            <Command size={23} strokeWidth={2.1} />
          </span>
          <span>
            <strong>OrbitHR</strong>
            <small>PEOPLE INTELLIGENCE</small>
          </span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          <a className="nav-item active" href="#overview">
            <LayoutDashboard size={18} />
            <span>Overview</span>
            <span className="nav-indicator" />
          </a>
          <a className="nav-item" href="#departments">
            <Building2 size={18} />
            <span>Departments</span>
          </a>
          <a className="nav-item" href="#workforce">
            <Users size={18} />
            <span>Workforce</span>
          </a>
          <a className="nav-item" href="#attrition">
            <BrainCircuit size={18} />
            <span>AI Intelligence</span>
            <span className="nav-tag">V3</span>
          </a>
          <a className="nav-item" href="#signals">
            <Activity size={18} />
            <span>People Signals</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="security-card">
            <ShieldCheck size={19} />
            <div>
              <strong>Responsible AI</strong>
              <span>Human-reviewed insights</span>
            </div>
          </div>
          <a className="nav-item" href="#settings">
            <Settings size={18} />
            <span>Settings</span>
          </a>
          <a className="nav-item" href="#help">
            <CircleHelp size={18} />
            <span>Help & support</span>
          </a>
          <div className="profile">
            <div className="avatar">HR</div>
            <div className="profile-copy">
              <strong>HR Workspace</strong>
              <span>People operations</span>
            </div>
            <ChevronDown size={16} />
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>Overview</strong>
          </div>
          <div className="topbar-actions">
            <span className="environment">
              <span className="status-dot" />
              DEVELOPMENT
            </span>
            <button className="icon-button" aria-label="Search">
              <Search size={18} />
            </button>
            <button className="icon-button" aria-label="Notifications">
              <Bell size={18} />
            </button>
            <div className="topbar-date">HR ANALYTICS</div>
          </div>
        </header>

        <div className="dashboard-content" id="overview">
          <div className="page-heading">
            <div>
              <div className="eyebrow">PEOPLE ANALYTICS / COMMAND CENTER</div>
              <h1>Workforce <span>Overview</span></h1>
              <p>
                A clearer view of your workforce, backed by operational HR data.
              </p>
            </div>
            <div className="heading-status">
              <span className="status-dot" />
              {loading ? "Syncing data" : error ? "Connection issue" : "Live API"}
            </div>
          </div>

          {error && (
            <div className="error-banner" role="alert">
              <div>
                <strong>Unable to retrieve workforce data</strong>
                <p>{error}</p>
                <span>
                  Confirm that FastAPI is running at {API_BASE} and that CORS
                  permits the frontend origin.
                </span>
              </div>
              <button
                className="retry-button"
                onClick={() => window.location.reload()}
              >
                Retry
              </button>
            </div>
          )}

          <SectionTitle
            eyebrow="01 / WORKFORCE SNAPSHOT"
            title="The essentials"
            detail="Current database aggregates · Operational HR"
          />

          <div className="metrics-grid" id="workforce">
            <MetricCard
              label="Total headcount"
              value={loading ? "—" : formatNumber(overview?.headcount.total ?? 0)}
              detail="Employees in the HR database"
              icon={Users}
              accent
            />
            <MetricCard
              label="Active employees"
              value={loading ? "—" : formatNumber(overview?.headcount.active ?? 0)}
              detail="Historical status records"
              icon={Activity}
            />
            <MetricCard
              label="Exited employees"
              value={loading ? "—" : formatNumber(overview?.headcount.exited ?? 0)}
              detail="Historical exit records"
              icon={ArrowDownRight}
            />
            <MetricCard
              label="Average annual salary"
              value={
                loading
                  ? "—"
                  : formatCurrency(overview?.workforce.average_annual_salary_inr ?? 0)
              }
              detail="INR · Database average"
              icon={Wallet}
            />
          </div>

          <div className="metrics-grid metrics-grid-secondary">
            <MetricCard
              label="Historical attrition rate"
              value={
                loading
                  ? "—"
                  : `${formatNumber(overview?.attrition.attrition_rate_percent ?? 0)}%`
              }
              detail="Exited records ÷ total employees"
              icon={BarChart3}
            />
            <MetricCard
              label="Avg. engagement"
              value={
                loading
                  ? "—"
                  : `${formatNumber(overview?.workforce_signals.average_engagement_score ?? 0)} / 10`
              }
              detail="Survey score average"
              icon={ArrowUpRight}
            />
            <MetricCard
              label="Avg. performance"
              value={
                loading
                  ? "—"
                  : `${formatNumber(overview?.workforce_signals.average_performance_rating ?? 0)} / 5`
              }
              detail="Performance review average"
              icon={Activity}
            />
            <MetricCard
              label="Avg. attendance hours"
              value={
                loading
                  ? "—"
                  : `${formatNumber(overview?.workforce_signals.average_attendance_hours ?? 0)}h`
              }
              detail="Recorded hours per attendance row"
              icon={Activity}
            />
          </div>

          <div className="section-gap" id="departments">
            <SectionTitle
              eyebrow="02 / ORGANIZATIONAL HEALTH"
              title="Department intelligence"
              detail="Compare workforce distribution and people signals"
            />
          </div>

          <div className="charts-grid">
            <article className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <h3>Headcount by department</h3>
                  <p>Employees recorded in each department</p>
                </div>
                <span className="panel-index">A</span>
              </div>
              <div className="chart-area">
                {loading ? (
                  <LoadingState />
                ) : departments.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={departments}
                      margin={{ top: 12, right: 8, left: -18, bottom: 36 }}
                    >
                      <CartesianGrid
                        stroke="#292824"
                        strokeDasharray="3 5"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#99958B", fontSize: 10 }}
                        angle={-32}
                        textAnchor="end"
                        interval={0}
                        axisLine={{ stroke: "#39362F" }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#99958B", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#191916",
                          border: "1px solid #51442F",
                          borderRadius: 8,
                          color: "#F5F0E6",
                        }}
                        formatter={(value) => [value, "Employees"]}
                      />
                      <Bar
                        dataKey="headcount"
                        fill={bronze}
                        radius={[4, 4, 0, 0]}
                        maxBarSize={36}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyState />
                )}
              </div>
            </article>

            <article className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <h3>Workforce composition</h3>
                  <p>Active and exited status records</p>
                </div>
                <span className="panel-index">B</span>
              </div>
              <div className="composition">
                <div className="donut-area">
                  {loading ? (
                    <LoadingState />
                  ) : pieData.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          innerRadius="67%"
                          outerRadius="88%"
                          paddingAngle={4}
                          stroke="none"
                        >
                          {pieData.map((entry, index) => (
                            <Cell
                              key={entry.name}
                              fill={index === 0 ? bronze : "#635D51"}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: "#191916",
                            border: "1px solid #51442F",
                            borderRadius: 8,
                            color: "#F5F0E6",
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyState />
                  )}
                  {!loading && overview && (
                    <div className="donut-center">
                      <strong>{formatNumber(overview.headcount.total)}</strong>
                      <span>EMPLOYEES</span>
                    </div>
                  )}
                </div>
                <div className="legend-list">
                  <div className="legend-item">
                    <span className="legend-dot legend-active" />
                    <span>Active records</span>
                    <strong>
                      {loading ? "—" : formatNumber(overview?.headcount.active ?? 0)}
                    </strong>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot legend-exited" />
                    <span>Exited records</span>
                    <strong>
                      {loading ? "—" : formatNumber(overview?.headcount.exited ?? 0)}
                    </strong>
                  </div>
                  <p className="chart-note">
                    Status record counts may not represent unique employees.
                  </p>
                </div>
              </div>
            </article>
          </div>

          <div className="section-gap" id="signals">
            <SectionTitle
              eyebrow="03 / PEOPLE SIGNALS"
              title="Engagement & performance"
              detail="Department-level averages from available records"
            />
          </div>

          <article className="panel chart-panel engagement-panel">
            <div className="panel-heading">
              <div>
                <h3>Department engagement</h3>
                <p>Average survey score · Scale of 10</p>
              </div>
              <span className="chart-unit">SCORE / 10</span>
            </div>
            <div className="chart-area chart-area-short">
              {loading ? (
                <LoadingState />
              ) : engagementData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={engagementData}
                    margin={{ top: 12, right: 10, left: -14, bottom: 30 }}
                  >
                    <CartesianGrid
                      stroke="#292824"
                      strokeDasharray="3 5"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#99958B", fontSize: 10 }}
                      angle={-25}
                      textAnchor="end"
                      interval={0}
                      axisLine={{ stroke: "#39362F" }}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[0, 10]}
                      tick={{ fill: "#99958B", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#191916",
                        border: "1px solid #51442F",
                        borderRadius: 8,
                        color: "#F5F0E6",
                      }}
                      formatter={(value) => [value, "Engagement"]}
                    />
                    <Bar
                      dataKey="average_engagement_score"
                      fill={bronze}
                      radius={[4, 4, 0, 0]}
                      maxBarSize={34}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState />
              )}
            </div>
          </article>

          <div className="section-gap" id="attrition">
            <SectionTitle
              eyebrow="04 / AI-ASSISTED DECISION SUPPORT"
              title="Attrition intelligence"
              detail="Research model · Separate synthetic dataset"
            />
          </div>

          <article className="research-card">
            <div className="research-icon">
              <BrainCircuit size={25} />
            </div>
            <div className="research-copy">
              <div className="research-overline">EVENT-BASED LOGISTIC REGRESSION</div>
              <h3>Explore predictive retention research</h3>
              <p>
                The v3 model uses synthetic employee histories, 90-day feature
                windows, and a 180-day outcome horizon. It is not connected to
                the operational employee database.
              </p>
              <div className="research-tags">
                <span>event-based-v3</span>
                <span>Explainable model</span>
                <span>Synthetic data only</span>
              </div>
            </div>
            <div className="research-status">
              <span className="status-dot" />
              Research
            </div>
          </article>

          <footer className="footer">
            <span>ORBIT HR <span className="footer-separator">/</span> PEOPLE INTELLIGENCE</span>
            <span>Operational metrics and model research are kept separate.</span>
          </footer>
        </div>
      </section>
    </main>
  );
}

function ClockIcon(props: React.ComponentProps<typeof Activity>) {
  return <Activity {...props} />;
}

function LoadingState() {
  return (
    <div className="loading-state">
      <LoaderCircle size={20} className="spin" />
      <span>Loading analytics</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="loading-state">
      <span>No data available</span>
    </div>
  );
}
