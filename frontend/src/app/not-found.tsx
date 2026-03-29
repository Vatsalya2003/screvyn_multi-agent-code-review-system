import Link from "next/link";

export default function NotFound() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center"
      style={{ background: "#080808", color: "#F5F0EB" }}
    >
      <div
        className="text-[11px] tracking-widest uppercase mb-6"
        style={{ color: "#555555" }}
      >
        404
      </div>
      <h1
        className="text-4xl font-semibold tracking-tight mb-3"
        style={{ letterSpacing: "-1px" }}
      >
        Page not found
      </h1>
      <p className="text-sm mb-8" style={{ color: "#999999" }}>
        This page doesn&apos;t exist or was moved.
      </p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="px-6 py-2.5 rounded-full text-sm font-medium transition-colors"
          style={{ background: "#F5F0EB", color: "#141414" }}
        >
          Go home
        </Link>
        <Link
          href="/dashboard"
          className="px-6 py-2.5 rounded-full text-sm transition-colors"
          style={{
            border: "1px solid rgba(85,85,85,0.25)",
            color: "#999999",
          }}
        >
          Dashboard
        </Link>
      </div>
    </div>
  );
}
