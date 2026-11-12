import { useState, useEffect, useMemo } from 'react'

export default function Positions({ isConfigured, onLoginClick, marketData, optionChain }) {
  const [positions, setPositions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    const fetchPositions = async () => {
      setIsRefreshing(true)
      try {
        const apiUrl = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : 'http://127.0.0.1:8000/api';
        const res = await fetch(`${apiUrl}/positions`)
        const data = await res.json()
        if (data.status === 'success') {
          setPositions(data.data || [])
          setError(null)
        } else {
          setError(data.message || 'Failed to fetch positions')
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
        setIsRefreshing(false)
      }
    }

    if (isConfigured) {
      fetchPositions()
      const interval = setInterval(fetchPositions, 3000)
      return () => clearInterval(interval)
    }
  }, [isConfigured])

  // Sort positions: active (qty != 0) first, closed (qty == 0) last
  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      const aActive = parseInt(a.netqty || 0) !== 0
      const bActive = parseInt(b.netqty || 0) !== 0
      if (aActive && !bActive) return -1
      if (!aActive && bActive) return 1
      return 0
    })
  }, [positions])

  // Compute Delta & Exposure
  const enrichedPositions = useMemo(() => {
    return sortedPositions.map(pos => {
      let delta = 0;
      let exposure = 0;
      const qty = parseInt(pos.netqty || 0);
      
      if (qty !== 0 && pos.strikeprice && pos.optiontype) {
        const strike = parseFloat(pos.strikeprice);
        const type = pos.optiontype.toUpperCase();
        const symbol = pos.symbolname ? pos.symbolname.toUpperCase() : '';
        
        if (symbol && optionChain && Array.isArray(optionChain[symbol])) {
          const row = optionChain[symbol].find(r => parseFloat(r.strike) === strike);
          const spot = marketData?.[symbol.toLowerCase()]?.spot || 0;
          
          let greekDelta = 0;
          if (row) {
            greekDelta = type === 'CE' ? row.call_delta : (type === 'PE' ? row.put_delta : 0);
          } else if (spot > 0) {
            // Fallback approximation if option is from a different expiry or not in chain
            if (type === 'CE') {
              greekDelta = strike < spot - 200 ? 1.0 : strike > spot + 200 ? 0.0 : 0.5;
            } else if (type === 'PE') {
              greekDelta = strike > spot + 200 ? -1.0 : strike < spot - 200 ? 0.0 : -0.5;
            }
          }
          
          if (typeof greekDelta === 'number') {
            delta = greekDelta * qty;
            exposure = delta * spot;
          }
        }
      }
      return { ...pos, delta, exposure };
    });
  }, [sortedPositions, optionChain, marketData]);

  const totalPnL = enrichedPositions.reduce((acc, pos) => acc + parseFloat(pos.pnl || 0), 0)
  const netDelta = enrichedPositions.reduce((acc, pos) => acc + (pos.delta || 0), 0)
  const netExposure = enrichedPositions.reduce((acc, pos) => acc + (pos.exposure || 0), 0)

  const handleLogout = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : 'http://127.0.0.1:8000/api';
      await fetch(`${apiUrl}/broker/logout`, { method: 'POST' })
      // The backend will restart and the frontend will detect isConfigured=false shortly.
      window.location.reload()
    } catch (e) {
      console.error(e)
    }
  }

  if (!isConfigured) {
    return (
      <div className="card fade-in" style={{ margin: 'var(--space-md)' }}>
        <div className="card-header">
          <span className="card-title">💼 Open Positions</span>
        </div>
        <div style={{ padding: '60px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Connect your broker account to view your live positions and real-time P&L directly on the dashboard.
          </div>
          <button 
            onClick={onLoginClick}
            style={{
              padding: '10px 24px', background: '#0f172a', color: 'white',
              border: 'none', borderRadius: '6px', fontWeight: 'bold',
              cursor: 'pointer', fontSize: '14px', letterSpacing: '0.5px'
            }}
          >
            LOGIN TO BROKER
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="card fade-in" style={{ margin: 'var(--space-md)' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">💼 Open Positions</span>
          <button 
            onClick={onLoginClick}
            style={{ 
              background: 'none', border: '1px solid #cbd5e1', borderRadius: '4px', 
              padding: '2px 8px', fontSize: '10px', color: '#64748b', cursor: 'pointer',
              fontWeight: 600
            }}
          >
            SWITCH ACCOUNT
          </button>
        </div>
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading positions from Angel One...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card fade-in" style={{ margin: 'var(--space-md)' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">💼 Open Positions</span>
          <button 
            onClick={onLoginClick}
            style={{ 
              background: 'none', border: '1px solid #cbd5e1', borderRadius: '4px', 
              padding: '2px 8px', fontSize: '10px', color: '#64748b', cursor: 'pointer',
              fontWeight: 600
            }}
          >
            SWITCH ACCOUNT
          </button>
        </div>
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--red)' }}>
          Error: {error}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', minWidth: 0 }}>
      <div className="card fade-in" style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', padding: '16px 24px', borderBottom: '1px solid #e2e8f0' }}>
          
          {/* Left Side: Title & Account Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="card-title" style={{ margin: 0 }}>💼 Open Positions ({positions.length})</span>
            {isConfigured && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#64748b', background: '#f8fafc', padding: '4px 8px', borderRadius: '4px', border: '1px solid #e2e8f0', fontWeight: 600 }}>
                <div style={{ width: '6px', height: '6px', background: isRefreshing ? '#f59e0b' : '#10b981', borderRadius: '50%', boxShadow: isRefreshing ? '0 0 6px rgba(245, 158, 11, 0.6)' : '0 0 6px rgba(16, 185, 129, 0.6)', transition: 'background 0.3s', animation: isRefreshing ? 'none' : 'pulse 2s infinite' }}></div>
                {isRefreshing ? 'Refreshing...' : 'Live'}
              </div>
            )}
            <div style={{ display: 'flex', gap: '8px', borderLeft: '1px solid #cbd5e1', paddingLeft: '12px' }}>
              <button 
                onClick={onLoginClick}
                style={{ 
                  background: '#f1f5f9', border: 'none', borderRadius: '4px', 
                  padding: '4px 10px', fontSize: '11px', color: '#475569', cursor: 'pointer',
                  fontWeight: 600, transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = '#e2e8f0'}
                onMouseOut={(e) => e.currentTarget.style.background = '#f1f5f9'}
              >
                SWITCH
              </button>
              <button 
                onClick={handleLogout}
                style={{ 
                  background: '#fee2e2', border: 'none', borderRadius: '4px', 
                  padding: '4px 10px', fontSize: '11px', color: '#b91c1c', cursor: 'pointer',
                  fontWeight: 600, transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = '#fca5a5'}
                onMouseOut={(e) => e.currentTarget.style.background = '#fee2e2'}
              >
                LOGOUT
              </button>
            </div>
          </div>

          {/* Right Side: Metrics */}
          <div style={{ display: 'flex', gap: '24px', alignItems: 'center', fontSize: '13px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.5px' }}>Net Delta</span>
              <span style={{ fontWeight: 700, color: netDelta > 0 ? 'var(--green)' : netDelta < 0 ? 'var(--red)' : '#0f172a' }}>
                {netDelta > 0 ? '+' : ''}{netDelta.toFixed(2)}
              </span>
            </div>
            
            <div style={{ width: '1px', height: '24px', background: '#cbd5e1' }}></div>
            
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.5px' }}>Exposure</span>
              <span style={{ fontWeight: 700, color: netExposure > 0 ? 'var(--green)' : netExposure < 0 ? 'var(--red)' : '#0f172a' }}>
                ₹{(netExposure / 100000).toFixed(2)}L
              </span>
            </div>

            <div style={{ width: '1px', height: '24px', background: '#cbd5e1' }}></div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.5px' }}>Total P&L</span>
              <span style={{ fontWeight: 800, fontSize: '15px', color: totalPnL >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {totalPnL >= 0 ? '+' : ''}₹{totalPnL.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
        
        {enrichedPositions.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No open positions found.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: '#64748b' }}>Symbol</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: '#64748b' }}>Qty</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: '#64748b' }}>Avg Price</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: '#64748b' }}>LTP</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: '#64748b' }}>Delta</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: '#64748b', textAlign: 'right' }}>P&L</th>
                </tr>
              </thead>
              <tbody>
                {enrichedPositions.map((pos, i) => {
                  const pnl = parseFloat(pos.pnl || 0)
                  const isClosed = parseInt(pos.netqty || 0) === 0
                  
                  const symbolBadge = pos.optiontype === 'CE' ? (
                    <span style={{ background: '#dcfce7', color: '#166534', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' }}>CE</span>
                  ) : pos.optiontype === 'PE' ? (
                    <span style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' }}>PE</span>
                  ) : null;
                  
                  const formattedExpiry = pos.expirydate ? new Date(pos.expirydate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '';

                  return (
                    <tr key={i} className="position-row" style={{ borderBottom: '1px solid #e2e8f0', transition: 'background 0.2s', opacity: isClosed ? 0.6 : 1, cursor: 'default' }}>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#0f172a' }}>
                            <span>{pos.symbolname ? `${pos.symbolname} ${parseInt(pos.strikeprice)}` : pos.tradingsymbol}</span>
                            {symbolBadge}
                          </div>
                          {formattedExpiry && <span style={{ fontSize: '10px', color: '#64748b', marginTop: '2px', fontWeight: 500 }}>Expiry: {formattedExpiry}</span>}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: parseInt(pos.netqty) > 0 ? '#059669' : parseInt(pos.netqty) < 0 ? '#dc2626' : '#0f172a' }}>
                        <div style={{ background: parseInt(pos.netqty) !== 0 ? '#f1f5f9' : 'transparent', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>
                          {pos.netqty}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)' }}>₹{parseFloat(pos.netprice).toFixed(2)}</td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)' }}>₹{parseFloat(pos.ltp).toFixed(2)}</td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: pos.delta > 0 ? '#059669' : pos.delta < 0 ? '#dc2626' : '#64748b', fontWeight: 500 }}>
                        {!isClosed && typeof pos.delta === 'number' ? (
                          <div style={{ background: pos.delta > 0 ? '#dcfce7' : pos.delta < 0 ? '#fee2e2' : '#f1f5f9', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>
                            {pos.delta > 0 ? `+${pos.delta.toFixed(2)}` : pos.delta.toFixed(2)}
                          </div>
                        ) : '—'}
                      </td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: pnl > 0 ? '#059669' : pnl < 0 ? '#dc2626' : '#0f172a', textAlign: 'right', fontSize: '13px' }}>
                        {pnl > 0 ? '+' : ''}₹{pnl.toFixed(2)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
