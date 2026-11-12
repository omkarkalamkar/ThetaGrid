import { useRef, useEffect, memo } from 'react'

const SpotCard = memo(function SpotCard({
  label,
  value,
  change,
  pointsChange,
  icon,
  suffix = '',
  extra = null,
  isDte = false,
  niftyDte,
  sensexDte,
  delay = 0,
}) {
  const prevValue = useRef(value)
  const cardRef = useRef(null)

  useEffect(() => {
    if (!isDte && value !== prevValue.current && cardRef.current) {
      const el = cardRef.current.querySelector('.spot-value')
      if (el) {
        el.classList.remove('value-flash')
        void el.offsetWidth // trigger reflow
        el.classList.add('value-flash')
      }
    }
    prevValue.current = value
  }, [value, isDte])

  const getChangeClass = () => {
    if (change > 0) return 'positive'
    if (change < 0) return 'negative'
    return 'neutral'
  }

  const changeClass = getChangeClass()

  const formatValue = (val) => {
    if (val === null || val === undefined) return '—'
    return typeof val === 'number' ? val.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) : val
  }

  const formatChange = (val) => {
    if (val === null || val === undefined) return null
    const sign = val > 0 ? '+' : ''
    return `${sign}${val.toFixed(2)}%`
  }

  const getDteColor = (dte) => {
    if (dte === null || dte === undefined) return 'var(--text-muted)'
    if (dte > 3) return '#10b981' // Green
    if (dte > 1) return '#f59e0b' // Orange/Amber
    return '#ef4444' // Red
  }

  if (isDte) {
    return (
      <div className={`card spot-card fade-in fade-in-delay-${delay}`}>
        <div className="card-header">
          <span className="card-title">{label}</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.4px', textTransform: 'uppercase' }}>NIFTY</div>
            <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: getDteColor(niftyDte), lineHeight: 1.15 }}>
              {niftyDte !== null && niftyDte !== undefined ? `${niftyDte}d` : '—'}
            </div>
          </div>
          <div style={{ width: '1px', height: '24px', background: '#e2e8f0' }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.4px', textTransform: 'uppercase' }}>SENSEX</div>
            <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: getDteColor(sensexDte), lineHeight: 1.15 }}>
              {sensexDte !== null && sensexDte !== undefined ? `${sensexDte}d` : '—'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={cardRef}
      className={`card spot-card fade-in fade-in-delay-${delay} ${changeClass}`}
    >
      <div className="card-header">
        <span className="card-title">{label}</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '14px' }}>
        <div className="spot-value" style={{ flexShrink: 0 }}>
          {formatValue(value)}{suffix}
        </div>

        {change !== null && change !== undefined && typeof change === 'number' && (
          <>
            <div style={{ width: '1px', height: '22px', background: '#e2e8f0', flexShrink: 0 }} />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
              <div className={`spot-change ${changeClass}`}>
                <span>{change > 0 ? '▲' : change < 0 ? '▼' : '●'}</span>
                <span>{formatChange(change)}</span>
              </div>
              {pointsChange !== null && pointsChange !== undefined && typeof pointsChange === 'number' && (
                <span className="spot-points">
                  {pointsChange > 0 ? '+' : ''}{Math.round(pointsChange)} pts
                </span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
})

export default SpotCard
