"use client";

import { useState } from "react";

const C = {
  surface: "#0D0D0D",
  surfaceRaised: "#141414",
  border: "rgba(85,85,85,0.12)",
  text: "#F5F0EB",
  muted: "#999999",
  hint: "#555555",
  p0: "#E24B4A",
  p1: "#EF9F27",
  p2: "#B8B0A8",
  security: "#7F77DD",
  performance: "#1D9E75",
  smell: "#D85A30",
  architecture: "#378ADD",
};

const MOCK_REVIEWS = [
  {
    id: "r1",
    repo: "screvyn",
    pr: 3,
    title: "Add rate limiting to webhook endpoint",
    author: "vatsalya2003",
    p0: 3,
    p1: 3,
    p2: 5,
    agents: ["security", "performance", "smell", "architecture"],
    duration: "24s",
    date: "2026-03-29",
  },
  {
    id: "r2",
    repo: "screvyn",
    pr: 2,
    title: "Refactor Celery task queue",
    author: "vatsalya2003",
    p0: 1,
    p1: 4,
    p2: 3,
    agents: ["security", "performance", "architecture"],
    duration: "21s",
    date: "2026-03-29",
  },
  {
    id: "r3",
    repo: "screvyn",
    pr: 1,
    title: "Initial multi-agent review system",
    author: "vatsalya2003",
    p0: 3,
    p1: 3,
    p2: 5,
    duration: "24s",
    agents: ["security", "performance", "smell", "architecture"],
    date: "2026-03-28",
  },
  {
    id: "r4",
    repo: "api-gateway",
    pr: 12,
    title: "Update auth middleware to JWT",
    author: "vatsalya2003",
    p0: 0,
    p1: 2,
    p2: 4,
    agents: ["security", "architecture"],
    duration: "18s",
    date: "2026-03-27",
  },
  {
    id: "r5",
    repo: "auth-service",
    pr: 8,
    title: "Fix session token storage",
    author: "vatsalya2003",
    p0: 1,
    p1: 0,
    p2: 2,
    agents: ["security", "performance"],
    duration: "12s",
    date: "2026-03-26",
  },
  {
    id: "r6",
    repo: "payment-api",
    pr: 45,
    title: "Add Stripe webhook handler",
    author: "vatsalya2003",
    p0: 0,
    p1: 0,
    p2: 1,
    agents: ["security"],
    duration: "9s",
    date: "2026-03-26",
  },
  {
    id: "r7",
    repo: "payment-api",
    pr: 44,
    title: "Migrate to idempotency keys",
    author: "vatsalya2003",
    p0: 0,
    p1: 1,
    p2: 2,
    agents: ["performance", "architecture"],
    duration: "15s",
    date: "2026-03-25",
  },
  {
    id: "r8",
    repo: "api-gateway",
    pr: 11,
    title: "Remove deprecated v1 endpoints",
    author: "vatsalya2003",
    p0: 0,
    p1: 0,
    p2: 3,
    agents: ["smell", "architecture"],
    duration: "11s",
    date: "2026-03-24",
  },
];

const AGENT_COLORS: Record<string, string> = {
  security: C.security,
  performance: C.performance,
  smell: C.smell,
  architecture: C.architecture,
};

function SeverityPills({ p0, p1, p2 }: { p0: number; p1: number; p2: number }) {
  return (
    <div className="flex gap-1 flex-wrap">
      {p0 > 0 && (
        <span
          className="text-[11px] px-2 py-0.5 rounded-full"
          style={{ background: "rgba(226,75,74,0.12)", color: C.p0 }}
        >
          {p0} P0
        </span>
      )}
      {p1 > 0 && (
        <span
          className="text-[11px] px-2 py-0.5 rounded-full"
          style={{ background: "rgba(239,159,39,0.12)", color: C.p1 }}
        >
          {p1} P1
        </span>
      )}
      {p2 > 0 && (
        <span
          className="text-[11px] px-2 py-0.5 rounded-full"
          style={{ background: "rgba(85,85,85,0.15)", color: C.p2 }}
        >
          {p2} P2
        </span>
      )}
      {p0 === 0 && p1 === 0 && p2 === 0 && (
        <span className="text-[11px]" style={{ color: C.hint }}>
          —
        </span>
      )}
    </div>
  );
}

const PAGE_SIZE = 6;

export default function ReviewsPage() {
  const [filter, setFilter] = useState("7d");
  const [page, setPage] = useState(1);

  const totalPages = Math.ceil(MOCK_REVIEWS.length / PAGE_SIZE);
  const paginated = MOCK_REVIEWS.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: C.text }}>
          Reviews
        </h1>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="text-xs px-3 py-1.5 rounded-lg focus:outline-none"
          style={{
            background: C.surfaceRaised,
            border: `1px solid ${C.border}`,
            color: C.text,
          }}
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      <div
        className="rounded-xl overflow-hidden"
        style={{ border: `1px solid ${C.border}` }}
      >
        <table className="w-full text-left">
          <thead>
            <tr style={{ background: C.surface }}>
              {["Repository", "PR", "Findings", "Agents", "Duration", "Date"].map(
                (h) => (
                  <th
                    key={h}
                    className="px-5 py-3 text-xs font-normal"
                    style={{
                      color: C.hint,
                      borderBottom: `1px solid ${C.border}`,
                    }}
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {paginated.map((r, i) => (
              <tr
                key={r.id}
                className="cursor-pointer transition-colors"
                style={{
                  background: i % 2 === 0 ? C.surface : "rgba(20,20,20,0.4)",
                  borderBottom: `1px solid ${C.border}`,
                }}
              >
                <td className="px-5 py-3.5">
                  <span className="text-sm font-medium" style={{ color: C.text }}>
                    {r.repo}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <div>
                    <div className="text-xs font-medium mb-0.5" style={{ color: C.text }}>
                      #{r.pr}
                    </div>
                    <div
                      className="text-[11px] max-w-[200px] truncate"
                      style={{ color: C.hint }}
                    >
                      {r.title}
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <SeverityPills p0={r.p0} p1={r.p1} p2={r.p2} />
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex gap-1 flex-wrap">
                    {r.agents.map((a) => (
                      <span
                        key={a}
                        className="text-[10px] px-1.5 py-0.5 rounded capitalize"
                        style={{
                          color: AGENT_COLORS[a] || C.muted,
                          background: `${AGENT_COLORS[a] || C.hint}15`,
                        }}
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-5 py-3.5 text-xs" style={{ color: C.muted }}>
                  {r.duration}
                </td>
                <td className="px-5 py-3.5 text-xs" style={{ color: C.muted }}>
                  {r.date}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        <div
          className="flex items-center justify-between px-5 py-3"
          style={{
            background: C.surface,
            borderTop: `1px solid ${C.border}`,
          }}
        >
          <span className="text-xs" style={{ color: C.hint }}>
            {MOCK_REVIEWS.length} reviews
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg text-xs transition-colors"
              style={
                page === 1
                  ? { color: C.hint, cursor: "not-allowed" }
                  : {
                      color: C.muted,
                      background: C.surfaceRaised,
                    }
              }
            >
              ← Prev
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className="w-7 h-7 rounded-lg text-xs transition-colors"
                style={
                  page === p
                    ? { background: "rgba(85,85,85,0.25)", color: C.text }
                    : { color: C.muted }
                }
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded-lg text-xs transition-colors"
              style={
                page === totalPages
                  ? { color: C.hint, cursor: "not-allowed" }
                  : {
                      color: C.muted,
                      background: C.surfaceRaised,
                    }
              }
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
