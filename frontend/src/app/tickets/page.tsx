import { DashboardShell } from "@/components/DashboardShell";
import { TicketsDashboard } from "@/components/TicketsDashboard";
export default function TicketsPage() {
  return (
    <DashboardShell title="Ticket Analytics" subtitle="Volume · SLA · Trends · Categories">
      <TicketsDashboard />
    </DashboardShell>
  );
}
