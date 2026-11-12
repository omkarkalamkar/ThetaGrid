import { useState, useEffect, useCallback, memo } from 'react'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : 'http://localhost:8000/api'

const BUILDUP_COLORS = {
  'Long Buildup':   '#16a34a',
  'Short Buildup':  '#dc2626',
  'Long Unwinding': '#ea580c',
  'Short Covering': '#2563eb',
  'Neutral':        '#94a3b8',
}

const BUILDUP_BG = {
  'Long Buildup':   'rgba(22,163,74,0.08)',
  'Short Buildup':  'rgba(220,38,38,0.08)',
  'Long Unwinding': 'rgba(234,88,12,0.08)',
  'Short Covering': 'rgba(37,99,235,0.08)',
}

const SENTIMENT_STYLES = {
  'Bullish': { color: '#16a34a', bg: 'rgba(22,163,74,0.08)',   border: 'rgba(22,163,74,0.25)',   label: '▲ BULLISH' },
  'Bearish': { color: '#dc2626', bg: 'rgba(220,38,38,0.08)',   border: 'rgba(220,38,38,0.25)',   label: '▼ BEARISH' },
  'Neutral': { color: '#64748b', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.25)', label: '→ NEUTRAL' },
}

const formatOI = (oi) => {
  if (!oi) return '0'
  const abs = Math.abs(oi)
  const prefix = oi > 0 ? '+' : ''
  if (abs >= 1e7) return `${prefix}${(oi / 1e7).toFixed(1)}Cr`
  if (abs >= 1e5) return `${prefix}${(oi / 1e5).toFixed(1)}L`
  if (abs >= 1e3) return `${prefix}${(oi / 1e3).toFixed(0)}K`
  return `${prefix}${oi}`
}

const OIBuildupPanel = memo(function OIBuildupPanel({ index }) {
  const [data, setData] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const resp = await fetch(`${API_URL}/buildup/${index}`)
      const json = await resp.json()
      setData(json)
    } catch (e) {
      console.error('[ThetaGrid] Buildup fetch error:', e)
    }
  }, [index])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (!data) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8', fontSize: '12px' }}>
      Loading...
    </div>
  )

  if (!data.has_baseline) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8', fontSize: '12px', textAlign: 'center', padding: '12px' }}>
      Waiting for first market tick to establish OI baseline
    </div>
  )

  const sentStyle = SENTIMENT_STYLES[data.sentiment] || SENTIMENT_STYLES['Neutral']
  const allCallTypes = Object.entries(data.call_counts || {}).filter(([k]) => k !== 'Neutral')
  const allPutTypes  = Object.entries(data.put_counts  || {}).filter(([k]) => k !== 'Neutral')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', height: '100%', fontSize: '12px', overflow: 'hidden' }}>

      {/* Sentiment + Net OI */}
      <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
        <div style={{
          padding: '5px 10px', borderRadius: '5px',
          backgroundColor: sentStyle.bg, border: `1px solid ${sentStyle.border}`,
          fontWeight: 700, fontSize: '10px', color: sentStyle.color,
          letterSpacing: '0.5px', display: 'flex', alignItems: 'center', minWidth: '85px', justifyContent: 'center'
        }}>
          {sentStyle.label}
        </div>
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px' }}>
          <div style={{ padding: '4px 8px', borderRadius: '5px', border: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '9px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>OTM Call Δ</div>
            <div style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: data.total_call_oi_change > 0 ? '#16a34a' : data.total_call_oi_change < 0 ? '#dc2626' : '#475569' }}>
              {formatOI(data.total_call_oi_change)}
            </div>
          </div>
          <div style={{ padding: '4px 8px', borderRadius: '5px', border: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '9px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>OTM Put Δ</div>
            <div style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: data.total_put_oi_change > 0 ? '#16a34a' : data.total_put_oi_change < 0 ? '#dc2626' : '#475569' }}>
              {formatOI(data.total_put_oi_change)}
            </div>
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', flexShrink: 0 }}>
        <div>
          <div style={{ fontSize: '9px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '4px', borderBottom: '1px solid #e2e8f0', paddingBottom: '2px' }}>Call Breakdown</div>
          {allCallTypes.map(([type, count]) => (
            <div key={type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 0', marginBottom: '2px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <div 
                  className={(type === 'Long Buildup' || type === 'Short Buildup') ? 'buildup-pulse' : ''}
                  style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: BUILDUP_COLORS[type] }}></div>
                <span style={{ 
                  color: type.includes('Short') ? '#0f172a' : '#94a3b8', 
                  fontWeight: type.includes('Short') ? 700 : 500, 
                  fontSize: '10px' 
                }}>{type}</span>
              </div>
              <span style={{ 
                  color: type.includes('Short') ? '#1e293b' : '#cbd5e1', 
                  fontWeight: type.includes('Short') ? 800 : 600, 
                  fontSize: '11px', 
                  fontFamily: 'var(--font-mono)', 
                  background: type.includes('Short') ? '#e2e8f0' : '#f8fafc', 
                  padding: '1px 6px', 
                  borderRadius: '4px' 
              }}>{count}</span>
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: '9px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '4px', borderBottom: '1px solid #e2e8f0', paddingBottom: '2px' }}>Put Breakdown</div>
          {allPutTypes.map(([type, count]) => (
            <div key={type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 0', marginBottom: '2px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <div 
                  className={(type === 'Long Buildup' || type === 'Short Buildup') ? 'buildup-pulse' : ''}
                  style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: BUILDUP_COLORS[type] }}></div>
                <span style={{ 
                  color: type.includes('Short') ? '#0f172a' : '#94a3b8', 
                  fontWeight: type.includes('Short') ? 700 : 500, 
                  fontSize: '10px' 
                }}>{type}</span>
              </div>
              <span style={{ 
                  color: type.includes('Short') ? '#1e293b' : '#cbd5e1', 
                  fontWeight: type.includes('Short') ? 800 : 600, 
                  fontSize: '11px', 
                  fontFamily: 'var(--font-mono)', 
                  background: type.includes('Short') ? '#e2e8f0' : '#f8fafc', 
                  padding: '1px 6px', 
                  borderRadius: '4px' 
              }}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ height: '1px', background: '#e2e8f0', flexShrink: 0, margin: '2px 0' }} />

      {/* Top Movers */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', flex: 1, minHeight: 0, overflow: 'auto' }}>
        <div>
          <div style={{ fontSize: '9px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '4px' }}>Top Call Movers</div>
          {(data.top_call_movers || []).length === 0
            ? <span style={{ fontSize: '11px', color: '#94a3b8' }}>No data</span>
            : data.top_call_movers.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px dashed #e2e8f0' }}>
              <span style={{ fontWeight: 700, color: '#334155', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{m.strike.toLocaleString('en-IN')}</span>
              <span 
                className={(m.buildup === 'Long Buildup' || m.buildup === 'Short Buildup') ? 'buildup-pulse' : ''}
                style={{ color: BUILDUP_COLORS[m.buildup], fontWeight: 700, fontSize: '11px', fontFamily: 'var(--font-mono)', display: 'inline-block' }}>{formatOI(m.oi_change)}</span>
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: '9px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '4px' }}>Top Put Movers</div>
          {(data.top_put_movers || []).length === 0
            ? <span style={{ fontSize: '11px', color: '#94a3b8' }}>No data</span>
            : data.top_put_movers.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px dashed #e2e8f0' }}>
              <span style={{ fontWeight: 700, color: '#334155', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{m.strike.toLocaleString('en-IN')}</span>
              <span 
                className={(m.buildup === 'Long Buildup' || m.buildup === 'Short Buildup') ? 'buildup-pulse' : ''}
                style={{ color: BUILDUP_COLORS[m.buildup], fontWeight: 700, fontSize: '11px', fontFamily: 'var(--font-mono)', display: 'inline-block' }}>{formatOI(m.oi_change)}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
})

export default OIBuildupPanel
