import { ReactNode } from 'react'

interface Props {
  title: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
  height?: number
}

export default function ChartCard({ title, subtitle, children, actions, height = 280 }: Props) {
  return (
    <div style={{
      background: 'var(--obsidian-800)',
      border: '1px solid #1a1f2e',
      borderRadius: '12px',
      padding: '20px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0' }}>{title}</h3>
          {subtitle && <p style={{ fontSize: '0.75rem', color: '#475569', marginTop: '2px' }}>{subtitle}</p>}
        </div>
        {actions}
      </div>
      <div style={{ height }}>
        {children}
      </div>
    </div>
  )
}
