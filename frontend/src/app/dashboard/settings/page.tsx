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
  performance: "#1D9E75",
  security: "#7F77DD",
};

const WEBHOOK_URL = "https://screvyn.yourdomain.com/api/webhook/github";
const RATE_USED = 18;
const RATE_LIMIT = 50;

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-xl p-6"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <h2
        className="text-sm font-medium mb-5"
        style={{ color: C.text, letterSpacing: "-0.3px" }}
      >
        {title}
      </h2>
      {children}
    </div>
  );
}

function StatusDot({ connected }: { connected: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: connected ? C.performance : C.p0 }}
      />
      <span
        className="text-[11px]"
        style={{ color: connected ? C.performance : C.p0 }}
      >
        {connected ? "Connected" : "Not connected"}
      </span>
    </span>
  );
}

function LabeledRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5 mb-5">
      <label className="text-xs" style={{ color: C.muted }}>
        {label}
      </label>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const [copied, setCopied] = useState(false);
  const [teamsUrl, setTeamsUrl] = useState("");
  const [emailRecipients, setEmailRecipients] = useState("");
  const [testStatus, setTestStatus] = useState<
    "idle" | "sending" | "sent" | "error"
  >("idle");

  function copyWebhook() {
    navigator.clipboard.writeText(WEBHOOK_URL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function testTeams() {
    if (!teamsUrl.trim()) return;
    setTestStatus("sending");
    await new Promise((r) => setTimeout(r, 1200));
    setTestStatus("sent");
    setTimeout(() => setTestStatus("idle"), 3000);
  }

  const ratePct = Math.round((RATE_USED / RATE_LIMIT) * 100);

  return (
    <div>
      <h1
        className="text-xl font-semibold tracking-tight mb-6"
        style={{ color: C.text }}
      >
        Settings
      </h1>

      <div className="flex flex-col gap-4 max-w-2xl">
        {/* Webhook */}
        <SectionCard title="Webhook configuration">
          <LabeledRow label="GitHub App">
            <div
              className="flex items-center justify-between px-4 py-3 rounded-lg"
              style={{ background: C.surfaceRaised, border: `1px solid ${C.border}` }}
            >
              <span className="text-sm" style={{ color: C.text }}>
                GitHub App
              </span>
              <StatusDot connected={true} />
            </div>
          </LabeledRow>

          <LabeledRow label="Webhook URL">
            <div
              className="flex items-center gap-2 px-4 py-3 rounded-lg"
              style={{ background: C.surfaceRaised, border: `1px solid ${C.border}` }}
            >
              <code
                className="flex-1 text-xs font-mono truncate"
                style={{ color: C.muted }}
              >
                {WEBHOOK_URL}
              </code>
              <button
                onClick={copyWebhook}
                className="text-[11px] px-2.5 py-1 rounded-md transition-colors shrink-0"
                style={{
                  background: copied
                    ? "rgba(29,158,117,0.12)"
                    : "rgba(85,85,85,0.2)",
                  color: copied ? C.performance : C.muted,
                }}
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </LabeledRow>

          <p className="text-[11px]" style={{ color: C.hint }}>
            Add this URL to your GitHub App webhook settings. Set the content
            type to <code>application/json</code>.
          </p>
        </SectionCard>

        {/* Notifications */}
        <SectionCard title="Notifications">
          <LabeledRow label="Microsoft Teams webhook URL">
            <div className="flex gap-2">
              <input
                type="url"
                value={teamsUrl}
                onChange={(e) => setTeamsUrl(e.target.value)}
                placeholder="https://outlook.office.com/webhook/..."
                className="flex-1 text-sm px-4 py-2.5 rounded-lg focus:outline-none"
                style={{
                  background: C.surfaceRaised,
                  border: `1px solid ${C.border}`,
                  color: C.text,
                }}
              />
              <button
                onClick={testTeams}
                disabled={!teamsUrl.trim() || testStatus === "sending"}
                className="text-xs px-4 py-2.5 rounded-lg font-medium transition-colors shrink-0"
                style={
                  testStatus === "sent"
                    ? { background: "rgba(29,158,117,0.12)", color: C.performance }
                    : testStatus === "sending"
                    ? { background: C.surfaceRaised, color: C.hint }
                    : {
                        background: "rgba(85,85,85,0.2)",
                        color: C.muted,
                      }
                }
              >
                {testStatus === "sending"
                  ? "Sending..."
                  : testStatus === "sent"
                  ? "Sent ✓"
                  : "Test"}
              </button>
            </div>
          </LabeledRow>

          <LabeledRow label="Email recipients">
            <input
              type="text"
              value={emailRecipients}
              onChange={(e) => setEmailRecipients(e.target.value)}
              placeholder="team@example.com, lead@example.com"
              className="text-sm px-4 py-2.5 rounded-lg focus:outline-none"
              style={{
                background: C.surfaceRaised,
                border: `1px solid ${C.border}`,
                color: C.text,
              }}
            />
            <p className="text-[11px]" style={{ color: C.hint }}>
              Separate multiple addresses with commas.
            </p>
          </LabeledRow>

          <LabeledRow label="Resend API">
            <div
              className="flex items-center justify-between px-4 py-3 rounded-lg"
              style={{ background: C.surfaceRaised, border: `1px solid ${C.border}` }}
            >
              <span className="text-sm" style={{ color: C.text }}>
                Resend
              </span>
              <StatusDot connected={false} />
            </div>
          </LabeledRow>
        </SectionCard>

        {/* Rate limiting */}
        <SectionCard title="Rate limiting">
          <div className="flex items-baseline justify-between mb-3">
            <span className="text-[13px]" style={{ color: C.muted }}>
              Reviews this month
            </span>
            <span className="text-sm font-medium" style={{ color: C.text }}>
              {RATE_USED}
              <span className="font-normal" style={{ color: C.hint }}>
                {" "}
                / {RATE_LIMIT}
              </span>
            </span>
          </div>

          <div
            className="h-2 rounded-full overflow-hidden mb-2"
            style={{ background: "rgba(85,85,85,0.2)" }}
          >
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${ratePct}%`,
                background:
                  ratePct > 80
                    ? C.p0
                    : ratePct > 60
                    ? "#EF9F27"
                    : C.performance,
              }}
            />
          </div>

          <p className="text-[11px]" style={{ color: C.hint }}>
            {RATE_LIMIT - RATE_USED} reviews remaining this month. Resets on
            April 1, 2026.
          </p>
        </SectionCard>

        {/* Save */}
        <div className="flex justify-end">
          <button
            className="px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
            style={{ background: "#F5F0EB", color: "#141414" }}
          >
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
}
