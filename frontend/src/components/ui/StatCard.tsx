interface Props {
  label: string
  value: string | number
  sub?: string
  accent?: 'green' | 'amber' | 'rose' | 'sky' | 'violet'
  trend?: number
  delay?: number
}

const accents = {
  green: 'var(--pulse-400)',
  amber: 'var(--amber-400)',
  rose: 'var(--rose-400)',
  sky: 'var(--sky-400)',
  violet: 'var(--violet-400)',
}

export default function StatCard({ label, value, sub, accent = 'green', trend, delay = 0 }: Props) {
  const color = accents[accent]
  return (
    <div
      className={`animate-fade-up stagger-${delay + 1}`}
      style={{
        background: 'var(--obsidian-800)',
        border: '1px solid #1a1f2e',
        borderRadius: '12px',
        padding: '20px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* accent strip */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
        background: `linear-gradient(90deg, ${color}33, ${color}, ${color}33)`,
      }} />
      <div style={{ fontSize: '0.72rem', color: '#475569', fontFamily: 'Syne, sans-serif', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>
        {label}
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 800, color, fontFamily: 'Syne, sans-serif', lineHeight: 1, letterSpacing: '-0.03em' }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px' }}>{sub}</div>
      )}
      {trend !== undefined && (
        <div style={{ fontSize: '0.75rem', color: trend >= 0 ? 'var(--pulse-400)' : 'var(--rose-400)', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
          {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}%
        </div>
      )}
    </div>
  )
}
