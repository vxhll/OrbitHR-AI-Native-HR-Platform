"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BriefcaseBusiness,
  CalendarDays,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileText,
  LayoutDashboard,
  LogOut,
  MapPin,
  MessageCircle,
  ShieldCheck,
  UserRound,
  Wallet,
  Users,
  BrainCircuit,
  Menu,
  X,
} from "lucide-react";
import styles from "./page.module.css";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type DataObject = Record<string, unknown>;
type DataSection = DataObject | DataObject[] | null;

type Profile = {
  employee?: DataObject;
  attrition?: DataSection;
  attendance?: DataSection;
  payroll?: DataSection;
  performance?: DataSection;
  engagement?: DataSection;
  leave?: DataSection;
};

function asObject(value: unknown): DataObject {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as DataObject)
    : {};
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString("en-IN");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function getRecordCount(section: DataSection): string {
  if (Array.isArray(section)) return section.length.toLocaleString("en-IN");
  const record = asObject(section);
  const count =
    record.record_count ??
    record.total_records ??
    record.count;

  return displayValue(count);
}

function getMetric(
  section: DataSection,
  key: string,
): unknown {
  if (Array.isArray(section)) return undefined;
  return asObject(section)[key];
}

function getSectionLength(section: DataSection): number | null {
  if (Array.isArray(section)) return section.length;
  const record = asObject(section);
  const count = record.record_count ?? record.total_records ?? record.count;
  return typeof count === "number" ? count : null;
}

function formatSalary(value: unknown): string {
  if (typeof value !== "number") return displayValue(value);
  return `₹${value.toLocaleString("en-IN")}`;
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  accent = false,
}: {
  label: string;
  value: unknown;
  detail: string;
  icon: LucideIcon;
  accent?: boolean;
}) {
  return (
    <article className={`${styles.metricCard} ${accent ? styles.metricCardAccent : ""}`}>
      <div className={styles.metricCardTop}>
        <span className={styles.metricLabel}>{label}</span>
        <span className={styles.metricIcon}>
          <Icon size={18} strokeWidth={1.7} />
        </span>
      </div>
      <div className={styles.metricValue}>{displayValue(value)}</div>
      <div className={styles.metricDetail}>{detail}</div>
    </article>
  );
}

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  return (
    <div className={styles.infoItem}>
      <span className={styles.infoLabel}>{label}</span>
      <strong className={styles.infoValue}>{displayValue(value)}</strong>
    </div>
  );
}

export default function MyEmployeeProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      const token = sessionStorage.getItem("orbithr_access_token");

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const userResponse = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });

        if (userResponse.status === 401 || userResponse.status === 403) {
          sessionStorage.removeItem("orbithr_access_token");
          sessionStorage.removeItem("orbithr_user");
          router.replace("/login");
          return;
        }

        if (!userResponse.ok) {
          throw new Error(
            `Session verification failed (${userResponse.status}).`,
          );
        }

        const user = await userResponse.json();

        if (!user.employee_id) {
          throw new Error("Your account is not linked to an employee record.");
        }

        const profileResponse = await fetch(
          `${API_BASE}/api/employees/${encodeURIComponent(user.employee_id)}/profile`,
          {
            headers: { Authorization: `Bearer ${token}` },
            cache: "no-store",
          },
        );

        if (profileResponse.status === 401 || profileResponse.status === 403) {
          throw new Error(
            "You are not authorized to view this employee profile.",
          );
        }

        if (!profileResponse.ok) {
          throw new Error(
            `Could not load employee profile (${profileResponse.status}).`,
          );
        }

        const data = await profileResponse.json();

        if (!cancelled) {
          setProfile(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Unable to load profile.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, [router]);

  function signOut() {
    sessionStorage.removeItem("orbithr_access_token");
    sessionStorage.removeItem("orbithr_user");
    router.replace("/login");
  }

  if (loading) {
    return (
      <main className={styles.loadingScreen}>
        <div className={styles.loadingBrand}>
          <span className={styles.brandMark}>
            <BrainCircuit size={21} />
          </span>
          <span>ORBIT<span className={styles.brandAccent}>HR</span></span>
        </div>
        <div className={styles.loader} />
        <p>Preparing your workspace</p>
      </main>
    );
  }

  if (error || !profile) {
    return (
      <main className={styles.loadingScreen}>
        <section className={styles.errorCard}>
          <span className={styles.errorIcon}>
            <ShieldCheck size={24} />
          </span>
          <p className={styles.eyebrow}>EMPLOYEE WORKSPACE</p>
          <h1>We couldn&apos;t load your profile</h1>
          <p className={styles.errorMessage}>
            {error || "No profile data was returned."}
          </p>
          <button
            className={styles.primaryButton}
            onClick={() => router.replace("/login")}
          >
            Return to sign in
          </button>
        </section>
      </main>
    );
  }

  const employee = profile.employee ?? {};
  const attendance = profile.attendance ?? null;
  const performance = profile.performance ?? null;
  const engagement = profile.engagement ?? null;
  const leave = profile.leave ?? null;
  const payroll = profile.payroll ?? null;

  const fullName = displayValue(employee.full_name);
  const initials =
    typeof employee.full_name === "string"
      ? employee.full_name
          .split(/\s+/)
          .filter(Boolean)
          .slice(0, 2)
          .map((part) => part[0])
          .join("")
          .toUpperCase()
      : "EM";

  const salary = employee.annual_base_salary_inr;
  const averageHours = getMetric(attendance, "average_hours_worked");
  const attendanceCount = getRecordCount(attendance);
  const absentDays = getMetric(attendance, "absent_days");

  const performanceCount =
    getSectionLength(performance) ?? getRecordCount(performance);
  const engagementCount =
    getSectionLength(engagement) ?? getRecordCount(engagement);
  const leaveCount = getRecordCount(leave);
  const payrollCount = getRecordCount(payroll);

  return (
    <main className={styles.dashboard}>
      {mobileMenuOpen && (
        <button
          aria-label="Close navigation overlay"
          className={styles.mobileOverlay}
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`${styles.sidebar} ${mobileMenuOpen ? styles.sidebarOpen : ""}`}
      >
        <div className={styles.sidebarTop}>
          <Link href="/" className={styles.brand}>
            <span className={styles.brandMark}>
              <BrainCircuit size={21} strokeWidth={1.8} />
            </span>
            <span className={styles.brandName}>
              ORBIT<span>HR</span>
              <small>PEOPLE INTELLIGENCE</small>
            </span>
          </Link>

          <button
            className={styles.mobileClose}
            aria-label="Close navigation"
            onClick={() => setMobileMenuOpen(false)}
          >
            <X size={19} />
          </button>
        </div>

        <div className={styles.navCaption}>WORKSPACE</div>
        <nav className={styles.navigation}>
          <Link
            href="/"
            className={styles.navLink}
            onClick={() => setMobileMenuOpen(false)}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
            <ChevronRight size={15} className={styles.navChevron} />
          </Link>

          <Link
            href="/employees/me"
            className={`${styles.navLink} ${styles.navLinkActive}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <UserRound size={18} />
            <span>My profile</span>
            <span className={styles.activeDot} />
          </Link>

          <Link
            href="/chat"
            className={styles.navLink}
            onClick={() => setMobileMenuOpen(false)}
          >
            <MessageCircle size={18} />
            <span>AI HR Assistant</span>
            <ChevronRight size={15} className={styles.navChevron} />
          </Link>

          <Link
            href="/attrition"
            className={styles.navLink}
            onClick={() => setMobileMenuOpen(false)}
          >
            <Activity size={18} />
            <span>Attrition intelligence</span>
            <ChevronRight size={15} className={styles.navChevron} />
          </Link>
        </nav>

        <div className={styles.sidebarBottom}>
          <div className={styles.helpCard}>
            <span className={styles.helpIcon}>
              <CircleHelp size={17} />
            </span>
            <strong>Need assistance?</strong>
            <p>Your employee workspace, in one place.</p>
          </div>

          <div className={styles.sidebarDivider} />

          <div className={styles.sidebarUser}>
            <div className={styles.avatarSmall}>{initials}</div>
            <div className={styles.sidebarUserInfo}>
              <strong>{fullName}</strong>
              <span>{displayValue(employee.employee_id)}</span>
            </div>
            <button
              className={styles.signOutIcon}
              onClick={signOut}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <div className={styles.mainArea}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <button
              className={styles.mobileMenu}
              aria-label="Open navigation"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu size={21} />
            </button>
            <div>
              <p className={styles.breadcrumb}>WORKSPACE / EMPLOYEE</p>
              <h2>My profile</h2>
            </div>
          </div>

          <div className={styles.topbarRight}>
            <span className={styles.secureBadge}>
              <ShieldCheck size={14} />
              Secure workspace
            </span>
            <div className={styles.topbarAvatar}>{initials}</div>
          </div>
        </header>

        <div className={styles.pageContent}>
          <section className={styles.welcomeRow}>
            <div>
              <p className={styles.eyebrow}>YOUR ORBITHR WORKSPACE</p>
              <h1>Your people profile<span>.</span></h1>
              <p className={styles.pageSubtitle}>
                Your employment information and workforce records, together in one place.
              </p>
            </div>
            <div className={styles.employeeIdBadge}>
              <span>EMPLOYEE ID</span>
              <strong>{displayValue(employee.employee_id)}</strong>
            </div>
          </section>

          <section className={styles.profileHero}>
            <div className={styles.profileIdentity}>
              <div className={styles.avatarLarge}>{initials}</div>
              <div className={styles.profileNameBlock}>
                <div className={styles.profileStatus}>
                  <span className={styles.statusDot} />
                  AUTHENTICATED EMPLOYEE
                </div>
                <h2>{fullName}</h2>
                <p>{displayValue(employee.job_role)}</p>
                <div className={styles.profileTags}>
                  <span>
                    <BriefcaseBusiness size={14} />
                    {displayValue(employee.job_level)}
                  </span>
                  <span>
                    <MapPin size={14} />
                    {displayValue(employee.work_location)}
                  </span>
                </div>
              </div>
            </div>

            <div className={styles.heroDivider} />

            <div className={styles.profileQuickFacts}>
              <div>
                <span>DEPARTMENT</span>
                <strong>
                  {displayValue(
                    employee.department_name ?? employee.department_id,
                  )}
                </strong>
              </div>
              <div>
                <span>JOINED ON</span>
                <strong>{displayValue(employee.hire_date)}</strong>
              </div>
              <div>
                <span>TENURE</span>
                <strong>
                  {employee.tenure_years_at_period_start == null
                    ? "—"
                    : `${displayValue(employee.tenure_years_at_period_start)} years`}
                </strong>
              </div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.eyebrow}>WORKFORCE SNAPSHOT</p>
                <h2>Your records at a glance</h2>
              </div>
              <span className={styles.sectionNote}>
                <Activity size={14} />
                Profile data
              </span>
            </div>

            <div className={styles.metricGrid}>
              <MetricCard
                label="Attendance records"
                value={attendanceCount}
                detail="Available attendance entries"
                icon={CalendarDays}
                accent
              />
              <MetricCard
                label="Average work hours"
                value={
                  averageHours == null
                    ? "—"
                    : `${displayValue(averageHours)} hrs`
                }
                detail="Average hours per recorded day"
                icon={Clock3}
              />
              <MetricCard
                label="Absent days"
                value={absentDays}
                detail="From available attendance data"
                icon={CalendarDays}
              />
              <MetricCard
                label="Performance records"
                value={performanceCount}
                detail="Available performance entries"
                icon={ArrowUpRight}
              />
              <MetricCard
                label="Engagement records"
                value={engagementCount}
                detail="Available engagement entries"
                icon={Users}
              />
              <MetricCard
                label="Leave records"
                value={leaveCount}
                detail="Available leave entries"
                icon={FileText}
              />
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.eyebrow}>EMPLOYMENT INFORMATION</p>
                <h2>Employee details</h2>
              </div>
              <span className={styles.sectionNote}>Personal record</span>
            </div>

            <div className={styles.detailsCard}>
              <div className={styles.detailsCardHeader}>
                <span className={styles.detailsHeaderIcon}>
                  <UserRound size={18} />
                </span>
                <div>
                  <h3>Employment overview</h3>
                  <p>Core information associated with your employee record.</p>
                </div>
              </div>

              <div className={styles.infoGrid}>
                <InfoItem label="Full name" value={employee.full_name} />
                <InfoItem label="Employee ID" value={employee.employee_id} />
                <InfoItem label="Job role" value={employee.job_role} />
                <InfoItem label="Job level" value={employee.job_level} />
                <InfoItem
                  label="Department"
                  value={employee.department_name ?? employee.department_id}
                />
                <InfoItem label="Work location" value={employee.work_location} />
                <InfoItem label="Hire date" value={employee.hire_date} />
                <InfoItem
                  label="Tenure at period start"
                  value={
                    employee.tenure_years_at_period_start == null
                      ? "—"
                      : `${displayValue(employee.tenure_years_at_period_start)} years`
                  }
                />
                <InfoItem label="Age" value={employee.age} />
                <InfoItem label="Education" value={employee.education} />
                <InfoItem label="Marital status" value={employee.marital_status} />
                <InfoItem
                  label="Annual base salary"
                  value={formatSalary(salary)}
                />
              </div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.eyebrow}>RECORDS & BENEFITS</p>
                <h2>More of your HR data</h2>
              </div>
            </div>

            <div className={styles.recordsGrid}>
              <article className={styles.recordCard}>
                <span className={styles.recordIcon}>
                  <Wallet size={19} />
                </span>
                <div className={styles.recordText}>
                  <h3>Payroll</h3>
                  <p>Payroll records available in your profile.</p>
                </div>
                <strong className={styles.recordCount}>{payrollCount}</strong>
              </article>

              <article className={styles.recordCard}>
                <span className={styles.recordIcon}>
                  <ArrowDownRight size={19} />
                </span>
                <div className={styles.recordText}>
                  <h3>Leave</h3>
                  <p>Leave records available in your profile.</p>
                </div>
                <strong className={styles.recordCount}>{leaveCount}</strong>
              </article>

              <article className={styles.recordCard}>
                <span className={styles.recordIcon}>
                  <BriefcaseBusiness size={19} />
                </span>
                <div className={styles.recordText}>
                  <h3>Performance</h3>
                  <p>Performance entries linked to your profile.</p>
                </div>
                <strong className={styles.recordCount}>
                  {displayValue(performanceCount)}
                </strong>
              </article>
            </div>
          </section>

          <footer className={styles.footer}>
            <div className={styles.footerBrand}>
              <span className={styles.footerMark}>
                <BrainCircuit size={15} />
              </span>
              <span>ORBIT<span>HR</span></span>
            </div>
            <p>
              <ShieldCheck size={13} />
              Your workspace is protected by authenticated access.
            </p>
            <span className={styles.footerVersion}>PEOPLE INTELLIGENCE</span>
          </footer>
        </div>
      </div>
    </main>
  );
}
