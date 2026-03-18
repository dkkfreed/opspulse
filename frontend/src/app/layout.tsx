import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpsPulse — Workforce & Market Intelligence",
  description: "Operations intelligence platform for workforce planning, ticket analytics, and market signals",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="scanline" aria-hidden />
        {children}
      </body>
    </html>
  );
}
