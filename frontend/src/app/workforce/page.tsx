import { DashboardShell } from "@/components/DashboardShell";
import { WorkforceDashboard } from "@/components/WorkforceDashboard";
export default function WorkforcePage() {
  return (
    <DashboardShell title="Workforce Planning" subtitle="Utilization · Scheduling · Staffing gaps">
      <WorkforceDashboard />
    </DashboardShell>
  );
}
