interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  badge?: string;
  action?: React.ReactNode;
}

export function SectionHeader({ title, subtitle, badge, action }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div className="flex items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-display font-semibold text-text-primary">{title}</h2>
            {badge && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-bg-elevated text-text-secondary border border-bg-border uppercase tracking-wider">
                {badge}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-text-muted mt-0.5 font-mono">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
