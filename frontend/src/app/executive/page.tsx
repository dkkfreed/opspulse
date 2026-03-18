import { DashboardShell } from "@/components/DashboardShell";
import { ExecutiveDashboard } from "@/components/ExecutiveDashboard";
export default function ExecutivePage() {
  return (
    <DashboardShell title="Executive Summary" subtitle="High-level view for leadership · Last 30 days">
      <ExecutiveDashboard />
    </DashboardShell>
  );
}
