import { memo } from 'react'

const IVGauge = memo(function IVGauge({ percentile, currentIV }) {
  const pct = percentile ?? 50
  const iv = currentIV ?? 0

  const getGaugeClass = () => {
    if (pct < 30) return 'low'
    if (pct < 70) return 'mid'
    return 'high'
  }

  const getLabel = () => {
    if (pct < 20) return 'Very Low — Avoid selling'
    if (pct < 40) return 'Low — Cautious selling'
    if (pct < 60) return 'Average — Normal premiums'
    if (pct < 80) return 'High — Good for selling ✓'
    return 'Very High — Premium selling zone ✓✓'
  }

  const getColor = () => {
    if (pct < 30) return 'var(--green)'
    if (pct < 70) return 'var(--amber)'
    return 'var(--red)'
  }

  return (
    <div className="iv-gauge">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', width: '100%' }}>
        <span className="gauge-value" style={{ color: getColor() }}>
          {pct.toFixed(0)}%
        </span>
        <span className="gauge-label">
          IV: {iv.toFixed(1)}%
        </span>
      </div>

      <div className="gauge-bar-track">
        <div
          className={`gauge-bar-fill ${getGaugeClass()}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>

      <div className="gauge-labels">
        <span>0%</span>
        <span style={{ color: getColor(), fontWeight: 600 }}>{getLabel()}</span>
        <span>100%</span>
      </div>
    </div>
  )
})

export default IVGauge
