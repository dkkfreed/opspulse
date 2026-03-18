import { DashboardShell } from "@/components/DashboardShell";
import { MarketDashboard } from "@/components/MarketDashboard";
export default function MarketPage() {
  return (
    <DashboardShell title="Market Signals" subtitle="Job postings · Demand indices · Talent supply">
      <MarketDashboard />
    </DashboardShell>
  );
}
