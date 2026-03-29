"use client";

// ─── Color constants ────────────────────────────────────────────────────────
const C = {
  bg: "#080808",
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

// ─── MetricCard ──────────────────────────────────────────────────────────────
function MetricCard({
  label,
  value,
  change,
  up,
}: {
  label: string;
  value: string;
  change: string;
  up: boolean;
}) {
  return (
    <div
      className="rounded-xl p-5"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <p className="text-xs mb-3" style={{ color: C.muted }}>
        {label}
      </p>
      <div className="flex items-baseline gap-3">
        <span
          className="text-[30px] font-semibold tracking-tight leading-none"
          style={{ color: C.text }}
        >
          {value}
        </span>
        <span
          className="text-[11px] px-2 py-0.5 rounded-full"
          style={
            up
              ? {
                  background: "rgba(29,158,117,0.1)",
                  color: C.performance,
                }
              : {
                  background: "rgba(226,75,74,0.1)",
                  color: C.p0,
                }
          }
        >
          {up ? "↑" : "↓"} {change}
        </span>
      </div>
    </div>
  );
}

// ─── SeverityBar ─────────────────────────────────────────────────────────────
function SeverityBar({ p0, p1, p2 }: { p0: number; p1: number; p2: number }) {
  const total = p0 + p1 + p2 || 1;
  return (
    <div
      className="rounded-xl p-5"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <p className="text-xs mb-4" style={{ color: C.muted }}>
        Severity breakdown
      </p>
      <div className="flex gap-0.5 h-2.5 rounded-full overflow-hidden mb-5">
        <div style={{ width: `${(p0 / total) * 100}%`, background: C.p0 }} />
        <div style={{ width: `${(p1 / total) * 100}%`, background: C.p1 }} />
        <div style={{ width: `${(p2 / total) * 100}%`, background: C.p2 }} />
      </div>
      <div className="flex gap-5 text-xs">
        {[
          { color: C.p0, label: "Blocking", count: p0 },
          { color: C.p1, label: "Important", count: p1 },
          { color: C.p2, label: "Nit", count: p2 },
        ].map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: s.color }}
            />
            <span style={{ color: C.muted }}>{s.label}</span>
            <span className="font-medium" style={{ color: C.text }}>
              {s.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── AgentPerformance ────────────────────────────────────────────────────────
function AgentPerformance() {
  const agents = [
    { name: "Security", findings: 12, color: C.security, pct: 85 },
    { name: "Performance", findings: 8, color: C.performance, pct: 60 },
    { name: "Code smell", findings: 15, color: C.smell, pct: 100 },
    { name: "Architecture", findings: 9, color: C.architecture, pct: 70 },
  ];

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <p className="text-xs mb-4" style={{ color: C.muted }}>
        Agent findings
      </p>
      <div className="flex flex-col gap-4">
        {agents.map((a) => (
          <div key={a.name}>
            <div className="flex justify-between text-xs mb-1.5">
              <span style={{ color: C.text }}>{a.name}</span>
              <span style={{ color: C.muted }}>{a.findings}</span>
            </div>
            <div
              className="h-1.5 rounded-full overflow-hidden"
              style={{ background: "rgba(85,85,85,0.2)" }}
            >
              <div
                className="h-full rounded-full"
                style={{ width: `${a.pct}%`, background: a.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── WeeklyChart ─────────────────────────────────────────────────────────────
function WeeklyChart() {
  const days = [
    { label: "Mon", reviews: 2, h: 30 },
    { label: "Tue", reviews: 5, h: 70 },
    { label: "Wed", reviews: 3, h: 45 },
    { label: "Thu", reviews: 7, h: 100 },
    { label: "Fri", reviews: 4, h: 55 },
    { label: "Sat", reviews: 1, h: 15 },
    { label: "Sun", reviews: 2, h: 30 },
  ];
  const maxH = Math.max(...days.map((d) => d.reviews));

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <p className="text-xs mb-1" style={{ color: C.muted }}>
        Reviews this week
      </p>
      <p
        className="text-[26px] font-semibold tracking-tight mb-5 leading-none"
        style={{ color: C.text }}
      >
        24
      </p>
      <div className="flex items-end gap-2 h-20">
        {days.map((d) => (
          <div key={d.label} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full rounded-sm"
              style={{
                height: `${d.h}%`,
                background:
                  d.reviews === maxH
                    ? C.performance
                    : "rgba(85,85,85,0.25)",
              }}
            />
            <span className="text-[10px]" style={{ color: C.hint }}>
              {d.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── RecentReviews ───────────────────────────────────────────────────────────
function SeverityPills({
  p0,
  p1,
  p2,
}: {
  p0: number;
  p1: number;
  p2: number;
}) {
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
    </div>
  );
}

function RecentReviews() {
  const reviews = [
    { repo: "screvyn", pr: 3, p0: 3, p1: 3, p2: 5, duration: "24s", time: "2 min ago" },
    { repo: "screvyn", pr: 1, p0: 3, p1: 3, p2: 5, duration: "24s", time: "1 hour ago" },
    { repo: "api-gateway", pr: 12, p0: 0, p1: 2, p2: 4, duration: "18s", time: "3 hours ago" },
    { repo: "auth-service", pr: 8, p0: 1, p1: 0, p2: 2, duration: "12s", time: "Yesterday" },
    { repo: "payment-api", pr: 45, p0: 0, p1: 0, p2: 1, duration: "9s", time: "Yesterday" },
  ];

  return (
    <div
      className="rounded-xl p-5 col-span-2"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <div className="flex justify-between items-center mb-4">
        <p className="text-xs" style={{ color: C.muted }}>
          Recent reviews
        </p>
        <select
          className="text-xs px-3 py-1.5 rounded-lg focus:outline-none"
          style={{
            background: C.surfaceRaised,
            border: `1px solid ${C.border}`,
            color: C.text,
          }}
        >
          <option>Last 7 days</option>
          <option>Last 30 days</option>
          <option>All time</option>
        </select>
      </div>
      <table className="w-full text-left">
        <thead>
          <tr
            className="text-xs"
            style={{ color: C.hint, borderBottom: `1px solid ${C.border}` }}
          >
            <th className="pb-2.5 font-normal">Repository</th>
            <th className="pb-2.5 font-normal">Findings</th>
            <th className="pb-2.5 font-normal">Duration</th>
            <th className="pb-2.5 font-normal">Time</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map((r, i) => (
            <tr
              key={i}
              className="transition-colors cursor-pointer"
              style={{ borderTop: `1px solid ${C.border}` }}
            >
              <td className="py-3 pr-4">
                <span className="text-sm font-medium" style={{ color: C.text }}>
                  {r.repo}
                </span>
                <span className="text-xs ml-1.5" style={{ color: C.hint }}>
                  #{r.pr}
                </span>
              </td>
              <td className="py-3 pr-4">
                <SeverityPills p0={r.p0} p1={r.p1} p2={r.p2} />
              </td>
              <td className="py-3 pr-4 text-xs" style={{ color: C.muted }}>
                {r.duration}
              </td>
              <td className="py-3 text-xs" style={{ color: C.muted }}>
                {r.time}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── QuickActions ────────────────────────────────────────────────────────────
function QuickActions() {
  const actions = [
    { icon: "▷", label: "Paste code for review", href: "/review" },
    { icon: "⚙", label: "Configure webhooks", href: "/dashboard/settings" },
    {
      icon: "◎",
      label: "View on GitHub",
      href: "https://github.com/Vatsalya2003/screvyn_multi-agent-code-review-system",
      external: true,
    },
  ];

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <p className="text-xs mb-4" style={{ color: C.muted }}>
        Quick actions
      </p>
      <div className="flex flex-col gap-2">
        {actions.map((a) => (
          <a
            key={a.label}
            href={a.href}
            target={a.external ? "_blank" : undefined}
            rel={a.external ? "noopener noreferrer" : undefined}
            className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-colors"
            style={{
              background: C.surfaceRaised,
              color: C.text,
            }}
          >
            <span style={{ color: C.muted, fontSize: "13px" }}>{a.icon}</span>
            {a.label}
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1
          className="text-xl font-semibold tracking-tight"
          style={{ color: C.text }}
        >
          Overview
        </h1>
        <select
          className="text-xs px-3 py-1.5 rounded-lg focus:outline-none"
          style={{
            background: C.surfaceRaised,
            border: `1px solid ${C.border}`,
            color: C.text,
          }}
        >
          <option>Last 7 days</option>
          <option>Last 30 days</option>
        </select>
      </div>

      {/* Row 1 — metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <MetricCard label="Total reviews" value="24" change="36%" up={true} />
        <MetricCard label="Total findings" value="127" change="12%" up={true} />
        <MetricCard label="Avg. duration" value="22s" change="8%" up={false} />
        <MetricCard label="P0 this week" value="6" change="2" up={true} />
      </div>

      {/* Row 2 — charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <SeverityBar p0={18} p1={42} p2={67} />
        <AgentPerformance />
        <WeeklyChart />
      </div>

      {/* Row 3 — table + quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <RecentReviews />
        <QuickActions />
      </div>
    </div>
  );
}
