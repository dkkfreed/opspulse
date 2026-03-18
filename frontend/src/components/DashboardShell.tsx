import { Sidebar } from "@/components/Sidebar";
import { cn } from "@/lib/utils";

interface Props {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  className?: string;
}

export function DashboardShell({ children, title, subtitle, className }: Props) {
  return (
    <div className="flex min-h-screen bg-bg-primary">
      <Sidebar />
      <main className="flex-1 ml-56 px-8 py-7">
        <div className="max-w-7xl mx-auto">
          {/* Page header */}
          <div className="mb-7 pb-5 border-b border-bg-border">
            <h1 className="text-xl font-display font-bold text-text-primary tracking-tight">{title}</h1>
            {subtitle && <p className="text-sm text-text-muted font-mono mt-1">{subtitle}</p>}
          </div>
          <div className={cn("animate-fade-in", className)}>
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
