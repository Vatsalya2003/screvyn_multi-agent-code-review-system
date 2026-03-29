import Link from "next/link";

function Navbar() {
  return (
    <nav className="flex items-center justify-between px-6 md:px-12 py-5 max-w-6xl mx-auto">
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: "#1A1A1A" }}
        >
          <span className="font-semibold text-lg" style={{ color: "#F5F0EB" }}>
            S
          </span>
        </div>
        <span
          className="text-lg font-medium tracking-tight"
          style={{ color: "#2D2D2D" }}
        >
          Screvyn
        </span>
      </div>
      <div className="hidden md:flex gap-8 items-center">
        <Link
          href="#how-it-works"
          className="text-sm transition-colors text-[#777777] hover:text-[#2D2D2D]"
        >
          How it works
        </Link>
        <Link
          href="#agents"
          className="text-sm transition-colors text-[#777777] hover:text-[#2D2D2D]"
        >
          Agents
        </Link>
        <Link
          href="https://github.com/Vatsalya2003/screvyn_multi-agent-code-review-system"
          className="text-sm transition-colors text-[#777777] hover:text-[#2D2D2D]"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </Link>
        <Link
          href="/dashboard"
          className="px-5 py-2 rounded-full text-sm font-medium transition-colors bg-[#1A1A1A] text-[#F5F0EB] hover:bg-[#2D2D2D]"
        >
          Dashboard
        </Link>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="max-w-3xl mx-auto text-center pt-20 pb-8 px-6">
      <div
        className="inline-block px-4 py-1.5 rounded-full text-xs tracking-widest mb-6 uppercase"
        style={{
          background: "rgba(26,26,26,0.06)",
          color: "#777777",
        }}
      >
        Code Review on Autopilot
      </div>
      <h1
        className="text-5xl md:text-6xl font-semibold tracking-tight leading-[1.08] mb-5"
        style={{ color: "#2D2D2D", letterSpacing: "-2px" }}
      >
        Every pull request.
        <br />
        Reviewed by AI.
        <br />
        Before a human looks.
      </h1>
      <p
        className="text-lg leading-relaxed max-w-lg mx-auto mb-9"
        style={{ color: "#777777" }}
      >
        Four specialist agents analyze your code in parallel — catching security
        holes, performance bugs, and architecture issues in under 30 seconds.
      </p>
      <div className="flex gap-3 justify-center flex-wrap">
        <Link
          href="/review"
          className="px-7 py-3 rounded-full text-[15px] font-medium transition-colors"
          style={{ background: "#1A1A1A", color: "#F5F0EB" }}
        >
          Try a review
        </Link>
        <Link
          href="https://github.com/Vatsalya2003/screvyn_multi-agent-code-review-system"
          className="px-7 py-3 rounded-full text-[15px] font-medium transition-colors"
          style={{ border: "1px solid #C8C0B8", color: "#2D2D2D" }}
          target="_blank"
          rel="noopener noreferrer"
        >
          View on GitHub
        </Link>
      </div>
    </section>
  );
}

function TerminalPreview() {
  return (
    <section className="max-w-2xl mx-auto px-6 pt-12 pb-4">
      <div
        className="rounded-2xl p-5 font-mono text-[13px] leading-7"
        style={{ background: "#1A1A1A", color: "#B8B0A8" }}
      >
        <div className="flex gap-2 mb-4">
          <div
            className="w-3 h-3 rounded-full"
            style={{ background: "#E24B4A" }}
          />
          <div
            className="w-3 h-3 rounded-full"
            style={{ background: "#EF9F27" }}
          />
          <div
            className="w-3 h-3 rounded-full"
            style={{ background: "#1D9E75" }}
          />
        </div>

        <div>
          <span style={{ color: "#E24B4A" }}>blocking</span>
          <span style={{ color: "#555555" }}> | </span>
          <span style={{ color: "#7F77DD" }}>Security</span>
          {": SQL Injection in get_user "}
          <span style={{ color: "#555555" }}>(line 12)</span>
        </div>
        <div className="text-xs mt-1" style={{ color: "#999999" }}>
          User input goes directly into the query. An attacker passes
        </div>
        <div className="text-xs" style={{ color: "#999999" }}>
          {`uid="1; DROP TABLE users" and your data is gone.`}
        </div>
        <div className="mt-3">
          <span style={{ color: "#555555" }}>flagged: </span>
          <span style={{ color: "rgba(226,75,74,0.8)" }}>
            {`db.execute(f"SELECT * WHERE id={uid}")`}
          </span>
        </div>
        <div>
          <span style={{ color: "#555555" }}>fix: </span>
          <span style={{ color: "#1D9E75" }}>
            {`db.execute("SELECT * WHERE id=?", (uid,))`}
          </span>
        </div>

        <div
          className="mt-4 pt-3"
          style={{ borderTop: "1px solid rgba(85,85,85,0.3)" }}
        >
          <span style={{ color: "#EF9F27" }}>important</span>
          <span style={{ color: "#555555" }}> | </span>
          <span style={{ color: "#378ADD" }}>Architecture</span>
          {": God class UserManager "}
          <span style={{ color: "#555555" }}>(line 40–65)</span>
          <div className="text-xs mt-1" style={{ color: "#999999" }}>
            UserManager handles DB, email, validation, and logging. Split it.
          </div>
        </div>

        <div
          className="mt-4 pt-3"
          style={{ borderTop: "1px solid rgba(85,85,85,0.3)" }}
        >
          <span style={{ color: "#B8B0A8" }}>nit</span>
          <span style={{ color: "#555555" }}> | </span>
          <span style={{ color: "#D85A30" }}>Code smell</span>
          {": Magic number 0.15 "}
          <span style={{ color: "#555555" }}>(line 36)</span>
          <div className="text-xs mt-1" style={{ color: "#999999" }}>
            Use a named constant for readability.
          </div>
        </div>

        <div className="mt-4 text-[11px]" style={{ color: "#555555" }}>
          Reviewed by security · performance · smell · architecture in 24s
        </div>
      </div>
    </section>
  );
}

function AgentCards() {
  const agents = [
    {
      name: "Security",
      desc: "OWASP Top 10, leaked secrets, SQL injection, XSS",
      bg: "rgba(127,119,221,0.08)",
      iconBg: "#7F77DD",
      text: "#7F77DD",
    },
    {
      name: "Performance",
      desc: "N+1 queries, O(n²) loops, memory leaks, blocking calls",
      bg: "rgba(29,158,117,0.08)",
      iconBg: "#1D9E75",
      text: "#1D9E75",
    },
    {
      name: "Code smell",
      desc: "Dead code, god classes, magic numbers, duplication",
      bg: "rgba(216,90,48,0.08)",
      iconBg: "#D85A30",
      text: "#D85A30",
    },
    {
      name: "Architecture",
      desc: "SOLID violations, tight coupling, missing patterns",
      bg: "rgba(55,138,221,0.08)",
      iconBg: "#378ADD",
      text: "#378ADD",
    },
  ];

  return (
    <section id="agents" className="max-w-4xl mx-auto px-6 pt-24">
      <h2
        className="text-[36px] font-semibold tracking-tight text-center mb-3"
        style={{ color: "#2D2D2D", letterSpacing: "-1px" }}
      >
        Four agents. One review.
      </h2>
      <p className="text-center text-base mb-12" style={{ color: "#777777" }}>
        Each agent is a specialist — like having four senior engineers on every PR.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {agents.map((a) => (
          <div
            key={a.name}
            className="rounded-xl p-5"
            style={{ background: a.bg }}
          >
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center mb-4"
              style={{ background: a.iconBg }}
            >
              <span className="text-white text-sm font-medium">{a.name[0]}</span>
            </div>
            <div
              className="text-[15px] font-medium mb-1"
              style={{ color: "#2D2D2D" }}
            >
              {a.name}
            </div>
            <div className="text-[13px] leading-relaxed" style={{ color: a.text }}>
              {a.desc}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      num: "1",
      title: "Push code or open a PR",
      desc: "GitHub sends a webhook to Screvyn. Signature verified, task enqueued in under 200ms.",
    },
    {
      num: "2",
      title: "Four agents analyze in parallel",
      desc: "AST parsing extracts code structure. Security, performance, smell, and architecture agents run simultaneously via LangGraph.",
    },
    {
      num: "3",
      title: "Review appears on your PR",
      desc: "Severity-ranked findings with explanations and fixes. Plus Teams, email, and dashboard notifications.",
    },
  ];

  return (
    <section id="how-it-works" className="max-w-2xl mx-auto px-6 pt-24">
      <h2
        className="text-[36px] font-semibold tracking-tight text-center mb-3"
        style={{ color: "#2D2D2D", letterSpacing: "-1px" }}
      >
        How it works
      </h2>
      <p className="text-center text-base mb-12" style={{ color: "#777777" }}>
        Three steps. Zero configuration after setup.
      </p>
      <div className="flex flex-col">
        {steps.map((s, i) => (
          <div
            key={s.num}
            className="flex gap-5 items-start py-6"
            style={
              i < steps.length - 1
                ? { borderBottom: "1px solid #DDD8D0" }
                : undefined
            }
          >
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "#1A1A1A" }}
            >
              <span
                className="text-[15px] font-medium"
                style={{ color: "#F5F0EB" }}
              >
                {s.num}
              </span>
            </div>
            <div>
              <div
                className="text-[17px] font-medium mb-1"
                style={{ color: "#2D2D2D" }}
              >
                {s.title}
              </div>
              <div
                className="text-sm leading-relaxed"
                style={{ color: "#777777" }}
              >
                {s.desc}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="max-w-2xl mx-auto px-6 py-24">
      <div
        className="rounded-2xl py-12 px-10 text-center"
        style={{ background: "#1A1A1A" }}
      >
        <h2
          className="text-[28px] font-semibold tracking-tight mb-3"
          style={{ color: "#F5F0EB", letterSpacing: "-1px" }}
        >
          Start reviewing in 5 minutes.
        </h2>
        <p className="text-[15px] mb-7" style={{ color: "#999999" }}>
          Open source. Free tier. No credit card.
        </p>
        <Link
          href="/review"
          className="inline-block px-8 py-3 rounded-full text-[15px] font-medium transition-colors"
          style={{ background: "#F5F0EB", color: "#1A1A1A" }}
        >
          Get started
        </Link>
      </div>
      <p className="text-center text-xs mt-8" style={{ color: "#B8B0A8" }}>
        Built by Vatsalya Dabhi
      </p>
    </section>
  );
}

export default function Home() {
  return (
    <main
      className="min-h-screen"
      style={{ background: "#F5F0EB", color: "#2D2D2D" }}
    >
      <Navbar />
      <Hero />
      <TerminalPreview />
      <AgentCards />
      <HowItWorks />
      <CTA />
    </main>
  );
}
