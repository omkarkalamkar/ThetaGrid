import { memo } from 'react'

const GreeksPanel = memo(function GreeksPanel({ greeks }) {
  if (!greeks) {
    return (
      <div className="greeks-grid">
        {['Δ', 'Γ', 'Θ', 'ν'].map((sym, i) => (
          <div className="greek-item" key={i}>
            <div className="greek-symbol">{sym}</div>
            <div className="greek-value">—</div>
            <div className="greek-label">{['Delta', 'Gamma', 'Theta', 'Vega'][i]}</div>
          </div>
        ))}
      </div>
    )
  }

  const items = [
    {
      symbol: 'Δ',
      label: 'Delta',
      value: greeks.delta,
      format: (v) => v?.toFixed(3),
      colorClass: 'delta',
    },
    {
      symbol: 'Γ',
      label: 'Gamma',
      value: greeks.gamma,
      format: (v) => v?.toFixed(4),
      colorClass: 'gamma',
    },
    {
      symbol: 'Θ',
      label: 'Theta',
      value: greeks.theta,
      format: (v) => `₹${v?.toFixed(2)}`,
      colorClass: 'theta',
    },
    {
      symbol: 'ν',
      label: 'Vega',
      value: greeks.vega,
      format: (v) => v?.toFixed(2),
      colorClass: 'vega',
    },
  ]

  return (
    <div className="greeks-grid">
      {items.map((item, i) => (
        <div className="greek-item" key={i}>
          <div className={`greek-symbol ${item.colorClass}`}>{item.symbol}</div>
          <div className="greek-value mono">{item.format(item.value)}</div>
          <div className="greek-label">{item.label}</div>
        </div>
      ))}
    </div>
  )
})

export default GreeksPanel
