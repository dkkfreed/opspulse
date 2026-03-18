"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Overview", icon: "◈" },
  { href: "/workforce", label: "Workforce", icon: "⬡" },
  { href: "/tickets", label: "Tickets", icon: "◆" },
  { href: "/forecasting", label: "Forecasting", icon: "◇" },
  { href: "/anomalies", label: "Anomalies", icon: "⚠" },
  { href: "/market", label: "Market", icon: "◉" },
  { href: "/executive", label: "Executive", icon: "▣" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 min-h-screen bg-bg-secondary border-r border-bg-border flex flex-col py-6 px-3 gap-1 fixed top-0 left-0 z-40">
      {/* Logo */}
      <div className="px-3 mb-6">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent-cyan-dim border border-accent-cyan/30 flex items-center justify-center">
            <span className="text-accent-cyan text-sm font-mono font-bold">○</span>
          </div>
          <div>
            <div className="text-sm font-display font-bold text-text-primary">OpsPulse</div>
            <div className="text-[10px] font-mono text-text-muted tracking-widest uppercase">Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      {nav.map(({ href, label, icon }) => {
        const active = path === href;
        return (
          <Link key={href} href={href} className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group",
            active
              ? "bg-accent-cyan-dim text-accent-cyan border border-accent-cyan/20"
              : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
          )}>
            <span className={cn(
              "text-base w-5 text-center font-mono transition-all",
              active ? "text-accent-cyan" : "text-text-muted group-hover:text-text-secondary"
            )}>{icon}</span>
            <span className="font-display text-[13px] font-medium">{label}</span>
            {active && <span className="ml-auto w-1 h-1 rounded-full bg-accent-cyan" />}
          </Link>
        );
      })}

      {/* Bottom status */}
      <div className="mt-auto px-3 py-3 rounded-lg bg-bg-card border border-bg-border">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse-slow" />
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Live</span>
        </div>
        <div className="text-[10px] font-mono text-text-muted">
          {new Date().toLocaleDateString("en-CA", { month: "short", day: "numeric", year: "numeric" })}
        </div>
      </div>
    </aside>
  );
}
