"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUp,
  BrainCircuit,
  CheckCircle2,
  CircleHelp,
  FileText,
  LoaderCircle,
  LogOut,
  MessageCircle,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import styles from "./page.module.css";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type SupportSource = {
  source?: string | null;
  policy_id?: string | null;
  section?: string | null;
  type?: string | null;
  employee_id?: string | null;
  pay_month?: string | null;
  payroll_id?: number | null;
  onboarding_case_id?: number | null;
  [key: string]: unknown;
};

type SupportResponse = {
  question: string;
  intent: string;
  confidence: number;
  answer: string;
  requires_human: boolean;
  sources: SupportSource[];
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: SupportResponse;
};

const suggestedQuestions = [
  {
    title: "Leave policies",
    question: "What is the annual paid leave entitlement?",
    icon: FileText,
  },
  {
    title: "Payroll support",
    question: "How can I understand my payroll information?",
    icon: CircleHelp,
  },
  {
    title: "Onboarding help",
    question: "What should I complete during onboarding?",
    icon: CheckCircle2,
  },
];


function sourceLabel(source: SupportSource): string {
  const labels: (string | number | null | undefined)[] = [
    source.policy_id,
    source.section,
    source.source,
    source.pay_month,
    source.payroll_id ? `Payroll record ${source.payroll_id}` : null,
    source.onboarding_case_id
      ? `Onboarding case ${source.onboarding_case_id}`
      : null,
  ];

  return labels
    .filter(
      (value): value is string | number =>
        (typeof value === "string" && value.trim().length > 0) ||
        typeof value === "number",
    )
    .map(String)
    .join(" · ");
}


export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [error, setError] = useState("");
  const [employeeName, setEmployeeName] = useState("Employee");
  const [employeeInitials, setEmployeeInitials] = useState("E");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const token = sessionStorage.getItem("orbithr_access_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    let cancelled = false;

    async function verifySession() {
      try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });

        if (response.status === 401 || response.status === 403) {
          sessionStorage.removeItem("orbithr_access_token");
          sessionStorage.removeItem("orbithr_user");
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error("Unable to verify your session. Please try again.");
        }

        const user = await response.json();

        if (!user.employee_id) {
          throw new Error("Your account is not linked to an employee record.");
        }

        if (!cancelled) {
          const savedName =
            typeof user.full_name === "string" && user.full_name.trim()
              ? user.full_name.trim()
              : typeof user.name === "string" && user.name.trim()
                ? user.name.trim()
                : "Employee";

          setEmployeeName(savedName);
          setEmployeeInitials(
            savedName
              .split(/\s+/)
              .slice(0, 2)
              .map((part: string) => part[0])
              .join("")
              .toUpperCase(),
          );
          sessionStorage.setItem("orbithr_user", JSON.stringify(user));
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Unable to verify your session.",
          );
        }
      } finally {
        if (!cancelled) setAuthChecking(false);
      }
    }

    void verifySession();

    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  function signOut() {
    sessionStorage.removeItem("orbithr_access_token");
    sessionStorage.removeItem("orbithr_user");
    router.replace("/login");
  }

  async function sendQuestion(
    event?: FormEvent<HTMLFormElement>,
    preset?: string,
  ) {
    event?.preventDefault();

    const text = (preset ?? question).trim();

    if (!text || loading) return;

    if (text.length < 3 || text.length > 1000) {
      setError("Enter a question between 3 and 1,000 characters.");
      return;
    }

    const token = sessionStorage.getItem("orbithr_access_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    const userMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content: text,
    };

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/support/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question: text }),
        cache: "no-store",
      });

      const body = await response.json().catch(() => null);

      if (response.status === 401 || response.status === 403) {
        if (response.status === 401) {
          sessionStorage.removeItem("orbithr_access_token");
          sessionStorage.removeItem("orbithr_user");
          router.replace("/login");
          return;
        }

        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : "You are not authorized to access this support service.",
        );
      }

      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : `Support request failed (HTTP ${response.status}).`,
        );
      }

      if (
        typeof body?.answer !== "string" ||
        typeof body?.intent !== "string"
      ) {
        throw new Error("The support service returned an unexpected response.");
      }

      const result = body as SupportResponse;

      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: result.answer,
          result,
        },
      ]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to contact HR support. Please try again.",
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  if (authChecking) {
    return (
      <main className={styles.loadingScreen}>
        <div className={styles.loadingBrand}>
          <BrainCircuit size={22} />
          <span>
            ORBIT<span>HR</span>
          </span>
        </div>
        <LoaderCircle className={styles.spinner} size={24} />
        <p>Verifying your secure session...</p>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <aside className={styles.sidebar}>
        <Link href="/employees/me" className={styles.brand}>
          <span className={styles.brandMark}>
            <BrainCircuit size={21} />
          </span>
          <span className={styles.brandName}>
            ORBIT<span>HR</span>
            <small>PEOPLE INTELLIGENCE</small>
          </span>
        </Link>

        <div className={styles.navCaption}>EMPLOYEE WORKSPACE</div>

        <Link href="/employees/me" className={styles.navLink}>
          <UserRound size={18} />
          <span>My profile</span>
        </Link>

        <Link href="/chat" className={`${styles.navLink} ${styles.navActive}`}>
          <MessageCircle size={18} />
          <span>AI HR Assistant</span>
          <span className={styles.activeDot} />
        </Link>

        <div className={styles.sidebarBottom}>
          <div className={styles.securityCard}>
            <ShieldCheck size={18} />
            <strong>Secure support</strong>
            <p>Your requests use your authenticated employee session.</p>
          </div>

          <div className={styles.userBlock}>
            <span className={styles.avatar}>{employeeInitials}</span>
            <span className={styles.userDetails}>
              <strong>{employeeName}</strong>
              <small>Authenticated employee</small>
            </span>
            <button
              type="button"
              onClick={signOut}
              className={styles.iconButton}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <section className={styles.main}>
        <header className={styles.topbar}>
          <Link href="/employees/me" className={styles.backLink}>
            <ArrowLeft size={16} />
            <span>My profile</span>
          </Link>

          <span className={styles.secureBadge}>
            <ShieldCheck size={14} />
            Secure workspace
          </span>
        </header>

        <div className={styles.chatLayout}>
          <div className={styles.chatHeading}>
            <span className={styles.headingIcon}>
              <Sparkles size={20} />
            </span>
            <div>
              <p className={styles.eyebrow}>ORBITHR INTELLIGENCE</p>
              <h1>AI HR Assistant<span>.</span></h1>
              <p className={styles.subtitle}>
                Ask about HR policies, payroll guidance, leave, and onboarding.
              </p>
            </div>
          </div>

          <section className={styles.conversation} aria-label="Chat conversation">
            {messages.length === 0 ? (
              <div className={styles.welcome}>
                <span className={styles.welcomeIcon}>
                  <BrainCircuit size={29} />
                </span>
                <h2>How can I help you today?</h2>
                <p>
                  Ask an HR question in your own words. I’ll use OrbitHR’s
                  support service to find the most relevant response.
                </p>

                <div className={styles.suggestions}>
                  {suggestedQuestions.map((item) => {
                    const Icon = item.icon;

                    return (
                      <button
                        type="button"
                        key={item.title}
                        className={styles.suggestion}
                        disabled={loading}
                        onClick={() => void sendQuestion(undefined, item.question)}
                      >
                        <Icon size={17} />
                        <span>
                          <strong>{item.title}</strong>
                          <small>{item.question}</small>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className={styles.messageList}>
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={`${styles.messageRow} ${
                      message.role === "user" ? styles.userRow : styles.assistantRow
                    }`}
                  >
                    <span
                      className={`${styles.messageAvatar} ${
                        message.role === "user" ? styles.userAvatar : ""
                      }`}
                    >
                      {message.role === "user" ? (
                        <UserRound size={16} />
                      ) : (
                        <BrainCircuit size={17} />
                      )}
                    </span>

                    <div className={styles.messageContent}>
                      <span className={styles.messageAuthor}>
                        {message.role === "user" ? "You" : "OrbitHR Assistant"}
                      </span>
                      <div className={styles.bubble}>
                        <p>{message.content}</p>
                      </div>

                      {message.result && (
                        <div className={styles.responseMeta}>
                          <span className={styles.intentBadge}>
                            {message.result.intent.replaceAll("_", " ")}
                          </span>

                          {message.result.requires_human && (
                            <div className={styles.humanNotice}>
                              <ShieldCheck size={16} />
                              <span>
                                <strong>Human review recommended</strong>
                                <small>
                                  Please contact your HR team for further assistance.
                                </small>
                              </span>
                            </div>
                          )}

                          {message.result.sources?.length > 0 && (
                            <details className={styles.sources}>
                              <summary>
                                <FileText size={15} />
                                Sources ({message.result.sources.length})
                              </summary>
                              <ul>
                                {message.result.sources.map((source, index) => (
                                  <li key={`${source.policy_id ?? source.source ?? "source"}-${index}`}>
                                    {sourceLabel(source) ||
                                      source.type ||
                                      "Reference provided by HR support"}
                                  </li>
                                ))}
                              </ul>
                            </details>
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                ))}

                {loading && (
                  <div className={`${styles.messageRow} ${styles.assistantRow}`}>
                    <span className={styles.messageAvatar}>
                      <BrainCircuit size={17} />
                    </span>
                    <div className={styles.messageContent}>
                      <span className={styles.messageAuthor}>OrbitHR Assistant</span>
                      <div className={styles.typing}>
                        <LoaderCircle className={styles.spinner} size={16} />
                        Checking your request...
                      </div>
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </section>

          {error && (
            <div className={styles.errorBanner} role="alert">
              <CircleHelp size={17} />
              <span>{error}</span>
              <button type="button" onClick={() => setError("")} aria-label="Dismiss error">
                ×
              </button>
            </div>
          )}

          <form className={styles.composer} onSubmit={(event) => void sendQuestion(event)}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask an HR question..."
              aria-label="Your HR question"
              rows={2}
              maxLength={1000}
              disabled={loading}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendQuestion();
                }
              }}
            />
            <div className={styles.composerFooter}>
              <span>Enter to send · Shift + Enter for a new line</span>
              <button
                type="submit"
                className={styles.sendButton}
                disabled={loading || question.trim().length < 3}
                aria-label="Send question"
              >
                {loading ? (
                  <LoaderCircle className={styles.spinner} size={18} />
                ) : (
                  <ArrowUp size={19} />
                )}
              </button>
            </div>
          </form>

          <p className={styles.disclaimer}>
            AI-generated responses may need verification. Sensitive or unresolved
            issues should be reviewed by your HR team.
          </p>
        </div>
      </section>
    </main>
  );
}
