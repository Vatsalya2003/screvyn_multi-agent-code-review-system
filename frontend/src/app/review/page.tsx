"use client";

import { useState } from "react";
import Link from "next/link";

const SAMPLE_CODE = `import sqlite3
import os

DB_PASSWORD = "admin123"

def get_user(user_id):
    conn = sqlite3.connect("prod.db")
    return conn.execute(f"SELECT * FROM users WHERE id = {user_id}")

def get_all_orders(user_ids):
    results = []
    for uid in user_ids:
        results.append(sqlite3.connect("prod.db").execute(
            f"SELECT * FROM orders WHERE user_id = {uid}"
        ))
    return results`;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Finding {
  type: string;
  severity: string;
  title: string;
  line_range: string;
  explanation: string;
  flagged_code: string;
  fixed_code: string;
  owasp_ref?: string;
}

interface ReviewResponse {
  findings: Finding[];
  p0_count: number;
  p1_count: number;
  p2_count: number;
  agents_completed: string[];
  review_duration_seconds: number;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  P0: { bg: "rgba(226,75,74,0.12)", text: "#E24B4A", label: "blocking" },
  P1: { bg: "rgba(239,159,39,0.12)", text: "#EF9F27", label: "important" },
  P2: { bg: "rgba(85,85,85,0.15)", text: "#B8B0A8", label: "nit" },
};

const AGENT_COLORS: Record<string, string> = {
  security: "#7F77DD",
  performance: "#1D9E75",
  smell: "#D85A30",
  architecture: "#378ADD",
};

function SeverityBadge({ severity }: { severity: string }) {
  const s = SEVERITY_STYLES[severity] || SEVERITY_STYLES.P2;
  return (
    <span
      className="text-[11px] px-2.5 py-0.5 rounded-full font-medium"
      style={{ background: s.bg, color: s.text }}
    >
      {s.label}
    </span>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const agentColor = AGENT_COLORS[finding.type] || "#999999";

  return (
    <div
      className="rounded-xl p-5"
      style={{
        background: "#0D0D0D",
        border: "1px solid rgba(85,85,85,0.15)",
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <SeverityBadge severity={finding.severity} />
        <span className="text-xs capitalize" style={{ color: agentColor }}>
          {finding.type}
        </span>
      </div>
      <h3
        className="text-sm font-medium mb-2 leading-snug"
        style={{ color: "#F5F0EB" }}
      >
        {finding.title}
      </h3>
      <p className="text-xs leading-relaxed mb-3" style={{ color: "#999999" }}>
        {finding.explanation}
      </p>

      {finding.owasp_ref && (
        <p className="text-[10px] mb-3" style={{ color: "#555555" }}>
          {finding.owasp_ref}
        </p>
      )}

      {finding.flagged_code && finding.flagged_code !== "N/A" && (
        <div className="mb-3">
          <p
            className="text-[10px] mb-1.5 uppercase tracking-wider"
            style={{ color: "#555555" }}
          >
            Flagged
          </p>
          <pre
            className="rounded-lg p-3 text-xs font-mono overflow-x-auto leading-5"
            style={{
              background: "#080808",
              color: "rgba(226,75,74,0.85)",
              border: "1px solid rgba(226,75,74,0.1)",
            }}
          >
            {finding.flagged_code}
          </pre>
        </div>
      )}

      {finding.fixed_code && finding.fixed_code !== "N/A" && (
        <div>
          <p
            className="text-[10px] mb-1.5 uppercase tracking-wider"
            style={{ color: "#555555" }}
          >
            Fix
          </p>
          <pre
            className="rounded-lg p-3 text-xs font-mono overflow-x-auto leading-5"
            style={{
              background: "#080808",
              color: "#1D9E75",
              border: "1px solid rgba(29,158,117,0.1)",
            }}
          >
            {finding.fixed_code}
          </pre>
        </div>
      )}

      {finding.line_range && finding.line_range !== "N/A" && (
        <p className="text-[10px] mt-3" style={{ color: "#555555" }}>
          Line {finding.line_range}
        </p>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <div
      className="w-7 h-7 rounded-full animate-spin"
      style={{
        border: "2px solid rgba(85,85,85,0.3)",
        borderTopColor: "#F5F0EB",
      }}
    />
  );
}

export default function ReviewPage() {
  const [code, setCode] = useState(SAMPLE_CODE);
  const [language, setLanguage] = useState("python");
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    setReview(null);

    try {
      const res = await fetch(`${API_URL}/api/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language }),
      });

      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setReview(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to API"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen" style={{ background: "#080808", color: "#F5F0EB" }}>
      {/* Nav */}
      <nav
        className="flex items-center justify-between px-8 py-4"
        style={{ borderBottom: "1px solid rgba(85,85,85,0.15)" }}
      >
        <Link href="/" className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{ background: "#F5F0EB" }}
          >
            <span className="font-bold text-sm" style={{ color: "#141414" }}>
              S
            </span>
          </div>
          <span className="text-sm font-medium" style={{ color: "#F5F0EB" }}>
            Screvyn
          </span>
        </Link>
        <Link
          href="/dashboard"
          className="text-xs transition-colors"
          style={{ color: "#999999" }}
        >
          Dashboard →
        </Link>
      </nav>

      <div className="max-w-6xl mx-auto px-8 py-8">
        <h1 className="text-xl font-semibold tracking-tight mb-1">
          Try a review
        </h1>
        <p className="text-sm mb-6" style={{ color: "#999999" }}>
          Paste your code below and see what four AI agents find.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left — editor */}
          <div className="flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <div className="flex gap-1.5">
                {["python", "javascript", "java"].map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLanguage(lang)}
                    className="text-xs px-3 py-1.5 rounded-lg transition-colors"
                    style={
                      language === lang
                        ? {
                            background: "rgba(85,85,85,0.2)",
                            color: "#F5F0EB",
                          }
                        : { color: "#999999" }
                    }
                  >
                    {lang}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setCode(SAMPLE_CODE)}
                className="text-[10px] transition-colors"
                style={{ color: "#999999" }}
              >
                Load sample
              </button>
            </div>

            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="flex-1 min-h-[500px] p-4 font-mono text-xs leading-6 resize-none focus:outline-none rounded-xl"
              style={{
                background: "#0D0D0D",
                border: "1px solid rgba(85,85,85,0.12)",
                color: "#F5F0EB",
                caretColor: "#F5F0EB",
              }}
              placeholder="Paste your code here..."
              spellCheck={false}
            />

            <button
              onClick={handleSubmit}
              disabled={loading || !code.trim()}
              className="mt-3 py-3 rounded-xl text-sm font-medium transition-colors"
              style={
                loading
                  ? {
                      background: "rgba(85,85,85,0.15)",
                      color: "#999999",
                      cursor: "wait",
                    }
                  : {
                      background: "#F5F0EB",
                      color: "#141414",
                    }
              }
            >
              {loading ? "Reviewing... (~25s)" : "Run review"}
            </button>
          </div>

          {/* Right — results */}
          <div className="flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs" style={{ color: "#999999" }}>
                Results
              </span>
              {review && (
                <div className="flex gap-1.5">
                  {review.p0_count > 0 && (
                    <span
                      className="text-[11px] px-2.5 py-0.5 rounded-full font-medium"
                      style={{
                        background: "rgba(226,75,74,0.12)",
                        color: "#E24B4A",
                      }}
                    >
                      {review.p0_count} P0
                    </span>
                  )}
                  {review.p1_count > 0 && (
                    <span
                      className="text-[11px] px-2.5 py-0.5 rounded-full font-medium"
                      style={{
                        background: "rgba(239,159,39,0.12)",
                        color: "#EF9F27",
                      }}
                    >
                      {review.p1_count} P1
                    </span>
                  )}
                  {review.p2_count > 0 && (
                    <span
                      className="text-[11px] px-2.5 py-0.5 rounded-full font-medium"
                      style={{
                        background: "rgba(85,85,85,0.15)",
                        color: "#B8B0A8",
                      }}
                    >
                      {review.p2_count} P2
                    </span>
                  )}
                </div>
              )}
            </div>

            <div
              className="flex-1 min-h-[500px] rounded-xl p-4 overflow-y-auto"
              style={{
                background: "rgba(13,13,13,0.5)",
                border: "1px solid rgba(85,85,85,0.1)",
              }}
            >
              {!review && !loading && !error && (
                <div className="h-full flex items-center justify-center">
                  <p className="text-sm text-center" style={{ color: "#555555" }}>
                    Paste code and click{" "}
                    <span style={{ color: "#777777" }}>Run review</span> to see
                    findings.
                  </p>
                </div>
              )}

              {loading && (
                <div className="h-full flex flex-col items-center justify-center gap-3">
                  <Spinner />
                  <p className="text-sm" style={{ color: "#999999" }}>
                    4 agents analyzing your code...
                  </p>
                </div>
              )}

              {error && (
                <div
                  className="rounded-lg p-4"
                  style={{
                    background: "rgba(226,75,74,0.08)",
                    border: "1px solid rgba(226,75,74,0.15)",
                  }}
                >
                  <p className="text-sm" style={{ color: "#E24B4A" }}>
                    {error}
                  </p>
                  <p className="text-xs mt-1" style={{ color: "#999999" }}>
                    Make sure the backend is running on {API_URL}
                  </p>
                </div>
              )}

              {review && (
                <div className="flex flex-col gap-3">
                  <div
                    className="flex items-center justify-between text-xs pb-3"
                    style={{
                      color: "#999999",
                      borderBottom: "1px solid rgba(85,85,85,0.1)",
                    }}
                  >
                    <span>
                      {review.findings.length} finding
                      {review.findings.length !== 1 ? "s" : ""} from{" "}
                      {review.agents_completed.join(", ")}
                    </span>
                    <span>{review.review_duration_seconds}s</span>
                  </div>
                  {review.findings.map((f, i) => (
                    <FindingCard key={i} finding={f} />
                  ))}
                  {review.findings.length === 0 && (
                    <div className="text-center py-12">
                      <p className="text-sm" style={{ color: "#1D9E75" }}>
                        No issues found. Clean code.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
