import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Screvyn — Code Review on Autopilot",
  description:
    "AI-powered multi-agent code review system. Four specialist agents analyze every pull request in parallel.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
