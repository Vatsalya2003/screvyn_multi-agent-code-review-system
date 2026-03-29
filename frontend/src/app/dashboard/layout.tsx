"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  {
    label: "Overview",
    href: "/dashboard",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <path d="M1 1h5.5v5.5H1V1zm7.5 0H14v5.5H8.5V1zM1 8.5h5.5V14H1V8.5zm7.5 0H14V14H8.5V8.5z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    label: "Reviews",
    href: "/dashboard/reviews",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <path d="M2 3h11M2 7.5h11M2 12h7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    label: "Try review",
    href: "/review",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <path d="M4 2.5L11.5 7.5L4 12.5V2.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    label: "Settings",
    href: "/dashboard/settings",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="2" stroke="currentColor" strokeWidth="1.2"/>
        <path d="M7.5 1v1.5M7.5 12.5V14M1 7.5h1.5M12.5 7.5H14M3.05 3.05l1.06 1.06M10.89 10.89l1.06 1.06M10.89 4.11l1.06-1.06M3.05 11.95l1.06-1.06" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
      </svg>
    ),
  },
];

function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-56 h-screen flex flex-col py-6 px-4 fixed left-0 top-0"
      style={{
        background: "#0D0D0D",
        borderRight: "1px solid rgba(85,85,85,0.12)",
      }}
    >
      <div className="flex items-center gap-2.5 px-2 mb-8">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: "#F5F0EB" }}
        >
          <span className="font-bold text-lg" style={{ color: "#141414" }}>
            S
          </span>
        </div>
        <span
          className="text-base font-medium tracking-tight"
          style={{ color: "#F5F0EB" }}
        >
          Screvyn
        </span>
      </div>

      <nav className="flex flex-col gap-0.5">
        {navItems.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors"
              style={
                active
                  ? {
                      background: "rgba(85,85,85,0.18)",
                      color: "#F5F0EB",
                    }
                  : { color: "#777777" }
              }
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-2">
        <Link
          href="/"
          className="text-xs flex items-center gap-1.5 transition-colors"
          style={{ color: "#555555" }}
        >
          <span>←</span>
          <span>Back to site</span>
        </Link>
      </div>
    </aside>
  );
}

function TopBar() {
  return (
    <header
      className="h-14 flex items-center justify-between px-8"
      style={{ borderBottom: "1px solid rgba(85,85,85,0.12)" }}
    >
      <div>
        <input
          type="text"
          placeholder="Search reviews..."
          className="px-4 py-2 text-sm rounded-lg w-64 focus:outline-none"
          style={{
            background: "#141414",
            border: "1px solid rgba(85,85,85,0.15)",
            color: "#F5F0EB",
          }}
        />
      </div>
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center"
        style={{ background: "#7F77DD" }}
      >
        <span className="text-white text-xs font-medium">VD</span>
      </div>
    </header>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className="min-h-screen"
      style={{ background: "#080808", color: "#F5F0EB" }}
    >
      <Sidebar />
      <div className="ml-56">
        <TopBar />
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
