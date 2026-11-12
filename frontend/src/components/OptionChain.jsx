import { useMemo, memo } from 'react'

const BUILDUP_STYLES = {
  'Long Buildup':    { label: 'LB', color: '#16a34a', bg: 'rgba(22,163,74,0.12)', title: 'Long Buildup — Price ↑ OI ↑ (Buyers entering)' },
  'Short Buildup':   { label: 'SB', color: '#dc2626', bg: 'rgba(220,38,38,0.12)', title: 'Short Buildup — Price ↓ OI ↑ (Sellers entering)' },
  'Long Unwinding':  { label: 'LU', color: '#ea580c', bg: 'rgba(234,88,12,0.12)', title: 'Long Unwinding — Price ↓ OI ↓ (Buyers exiting)' },
  'Short Covering':  { label: 'SC', color: '#2563eb', bg: 'rgba(37,99,235,0.12)', title: 'Short Covering — Price ↑ OI ↓ (Sellers exiting)' },
  'Neutral':         { label: '—',  color: 'var(--text-muted)', bg: 'transparent', title: 'Neutral — No significant change' },
}

const BuildupBadge = ({ type }) => {
  const style = BUILDUP_STYLES[type] || BUILDUP_STYLES['Neutral']
  if (type === 'Neutral') return <span style={{ color: style.color, fontSize: '11px' }}>—</span>
  return (
    <span
      className={(type === 'Long Buildup' || type === 'Short Buildup') ? 'buildup-pulse' : ''}
      title={style.title}
      style={{
        display: 'inline-block',
        padding: '1px 5px',
        borderRadius: '3px',
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.3px',
        color: style.color,
        backgroundColor: style.bg,
        border: `1px solid ${style.color}25`,
        cursor: 'help',
      }}
    >
      {style.label}
    </span>
  )
}

const OptionChain = memo(function OptionChain({ chain, atmStrike }) {
  const displayChain = useMemo(() => {
    if (!chain || chain.length === 0) return []

    const atm = atmStrike || chain[Math.floor(chain.length / 2)]?.strike
    const strikeGap = chain.length > 1 ? Math.abs(chain[1].strike - chain[0].strike) : 50

    return chain
      .filter(item => Math.abs(item.strike - atm) <= strikeGap * 12)
      .map(item => ({
        ...item,
        isAtm: item.strike === atm,
        isITMCall: item.strike < atm,
        isITMPut: item.strike > atm,
      }))
  }, [chain, atmStrike])

  if (displayChain.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
        Loading option chain...
      </div>
    )
  }

  const formatOI = (oi) => {
    if (oi >= 1e7) return `${(oi / 1e7).toFixed(2)}Cr`
    if (oi >= 1e5) return `${(oi / 1e5).toFixed(1)}L`
    if (oi >= 1e3) return `${(oi / 1e3).toFixed(0)}K`
    return oi?.toString() || '0'
  }

  const formatOIChange = (change) => {
    if (!change) return '—'
    const prefix = change > 0 ? '+' : ''
    if (Math.abs(change) >= 1e5) return `${prefix}${(change / 1e5).toFixed(1)}L`
    if (Math.abs(change) >= 1e3) return `${prefix}${(change / 1e3).toFixed(0)}K`
    return `${prefix}${change}`
  }

  return (
    <div className="option-chain-scroll">
      <table className="option-chain-table">
        <thead>
          <tr>
            <th colSpan="6" style={{ color: 'var(--red)', borderRight: '1px solid var(--border-primary)' }}>
              CALLS
            </th>
            <th style={{ color: 'var(--text-accent)' }}>STRIKE</th>
            <th colSpan="6" style={{ color: 'var(--green)', borderLeft: '1px solid var(--border-primary)' }}>
              PUTS
            </th>
          </tr>
          <tr>
            <th>Buildup</th>
            <th>OI</th>
            <th>ΔOI</th>
            <th>IV</th>
            <th>LTP</th>
            <th style={{ borderRight: '1px solid var(--border-primary)' }}>Delta</th>
            <th></th>
            <th style={{ borderLeft: '1px solid var(--border-primary)' }}>Delta</th>
            <th>LTP</th>
            <th>IV</th>
            <th>ΔOI</th>
            <th>OI</th>
            <th>Buildup</th>
          </tr>
        </thead>
        <tbody>
          {displayChain.map((item) => (
            <tr key={item.strike} className={item.isAtm ? 'atm-row' : ''}>
              {/* Call side */}
              <td className={item.isITMCall ? '' : 'call-side'}>
                <BuildupBadge type={item.call_buildup || 'Neutral'} />
              </td>
              <td className={item.isITMCall ? '' : 'call-side'}>
                {formatOI(item.call_oi)}
              </td>
              <td className={item.isITMCall ? '' : 'call-side'}>
                <span style={{
                  color: item.call_oi_change > 0 ? 'var(--green)' : item.call_oi_change < 0 ? 'var(--red)' : 'var(--text-muted)'
                }}>
                  {formatOIChange(item.call_oi_change)}
                </span>
              </td>
              <td className={item.isITMCall ? '' : 'call-side'}>
                {item.call_iv?.toFixed(1)}
              </td>
              <td className={item.isITMCall ? '' : 'call-side'} style={{ fontWeight: 600 }}>
                {item.call_ltp?.toFixed(2)}
              </td>
              <td className={item.isITMCall ? '' : 'call-side'} style={{ borderRight: '1px solid var(--border-primary)' }}>
                {item.call_delta?.toFixed(2)}
              </td>

              {/* Strike */}
              <td className="strike-col">
                {item.strike.toLocaleString('en-IN')}
              </td>

              {/* Put side */}
              <td className={item.isITMPut ? '' : 'put-side'} style={{ borderLeft: '1px solid var(--border-primary)' }}>
                {item.put_delta?.toFixed(2)}
              </td>
              <td className={item.isITMPut ? '' : 'put-side'} style={{ fontWeight: 600 }}>
                {item.put_ltp?.toFixed(2)}
              </td>
              <td className={item.isITMPut ? '' : 'put-side'}>
                {item.put_iv?.toFixed(1)}
              </td>
              <td className={item.isITMPut ? '' : 'put-side'}>
                <span style={{
                  color: item.put_oi_change > 0 ? 'var(--green)' : item.put_oi_change < 0 ? 'var(--red)' : 'var(--text-muted)'
                }}>
                  {formatOIChange(item.put_oi_change)}
                </span>
              </td>
              <td className={item.isITMPut ? '' : 'put-side'}>
                {formatOI(item.put_oi)}
              </td>
              <td className={item.isITMPut ? '' : 'put-side'}>
                <BuildupBadge type={item.put_buildup || 'Neutral'} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
})

export default OptionChain
