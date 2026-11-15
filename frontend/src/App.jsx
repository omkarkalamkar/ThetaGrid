import { useState, useEffect, useRef, useCallback } from 'react'
import './index.css'
import TopBar from './components/TopBar'
import SpotCard from './components/SpotCard'
import StraddleChart from './components/StraddleChart'
import KeyLevels from './components/KeyLevels'
import OIHeatmap from './components/OIHeatmap'
import IVGauge from './components/IVGauge'
import GreeksPanel from './components/GreeksPanel'
import OptionChain from './components/OptionChain'
import Positions from './components/Positions'
import OIBuildupPanel from './components/OIBuildupPanel'
import BrokerLoginModal from './components/BrokerLoginModal'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : 'http://localhost:8000/api'

function App() {
  const [marketData, setMarketData] = useState(null)
  const [straddleHistory, setStraddleHistory] = useState({ NIFTY: [], SENSEX: [] })
  const [optionChain, setOptionChain] = useState({ NIFTY: [], SENSEX: [] })
  const [selectedIndex, setSelectedIndex] = useState('NIFTY')
  const [connected, setConnected] = useState(false)
  const [isDemo, setIsDemo] = useState(true)
  const [isConfigured, setIsConfigured] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [mobileView, setMobileView] = useState('home') // home, levels, straddle, chain, buildup
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  useEffect(() => {
    fetch(`${API_URL}/status`)
      .then(r => r.json())
      .then(d => setIsConfigured(d.is_configured))
      .catch(console.error)
  }, [])

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      setConnected(true)
      console.log('[ThetaGrid] WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setMarketData(data)
        setIsDemo(data.demo_mode || false)

        // Append straddle history (1 point per minute, live updating last point)
        setStraddleHistory(prev => {
          const updated = { ...prev }
          for (const idx of ['NIFTY', 'SENSEX']) {
            const idxLower = idx.toLowerCase()
            if (data[idxLower]) {
              // Only record if this premium is from live data
              // TEMPORARILY DISABLED for weekend testing
              // if (!data[`_${idxLower}_live_premium`]) continue

              const premium = data[idxLower].straddle_premium
              // Reject obviously glitched values
              const maxSane = idx === 'NIFTY' ? 600 : 1600
              if (!premium || premium <= 0 || premium > maxSane) continue

              const currentHM = data.timestamp.substring(0, 5)
              
              // Ensure we only plot intraday chart during standard market hours
              // TEMPORARILY DISABLED for weekend testing
              // if (currentHM < '09:15' || currentHM > '15:30') continue

              const newPoint = {
                time: data.timestamp,
                premium: premium,
                vwap: data[idxLower].vwap || premium,
              }
              
              const history = [...(prev[idx] || [])]

              if (history.length > 0) {
                const lastPoint = history[history.length - 1]
                const lastHM = lastPoint.time.substring(0, 5)
                
                if (currentHM === lastHM) {
                  // Same minute, update live
                  history[history.length - 1] = newPoint
                } else {
                  // New minute, append
                  history.push(newPoint)
                }
              } else {
                history.push(newPoint)
              }
              
              // Keep entire day (max ~375 mins)
              updated[idx] = history.slice(-400)
            }
          }
          return updated
        })
      } catch (e) {
        console.error('[ThetaGrid] Parse error:', e)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      console.log('[ThetaGrid] WebSocket disconnected. Reconnecting...')
      reconnectTimer.current = setTimeout(connectWebSocket, 3000)
    }

    ws.onerror = (err) => {
      console.error('[ThetaGrid] WebSocket error:', err)
      ws.close()
    }

    wsRef.current = ws
  }, [])

  // Fetch option chain data
  const fetchOptionChain = useCallback(async (index) => {
    try {
      const resp = await fetch(`${API_URL}/option-chain/${index}`)
      const data = await resp.json()
      if (data.chain) {
        setOptionChain(prev => ({ ...prev, [index]: data.chain }))
      }
    } catch (e) {
      console.error('[ThetaGrid] Option chain fetch error:', e)
    }
  }, [])

  // Fetch straddle history
  const fetchStraddleHistory = useCallback(async (index) => {
    try {
      const resp = await fetch(`${API_URL}/straddle-history/${index}`)
      const data = await resp.json()
      if (data.history) {
        setStraddleHistory(prev => ({ ...prev, [index]: data.history }))
      }
    } catch (e) {
      console.error('[ThetaGrid] Straddle history fetch error:', e)
    }
  }, [])

  useEffect(() => {
    connectWebSocket()
    // Fetch initial option chains and history
    fetchOptionChain('NIFTY')
    fetchOptionChain('SENSEX')
    fetchStraddleHistory('NIFTY')
    fetchStraddleHistory('SENSEX')

    // Refresh data every 30s
    const interval = setInterval(() => {
      fetchOptionChain('NIFTY')
      fetchOptionChain('SENSEX')
      fetchStraddleHistory('NIFTY')
      fetchStraddleHistory('SENSEX')
    }, 30000)

    return () => {
      clearInterval(interval)
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connectWebSocket, fetchOptionChain])

  const idxData = marketData?.[selectedIndex.toLowerCase()]

  return (
    <div className="app">
      <BrokerLoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />
      
      <TopBar 
        connected={connected} 
        isDemo={isDemo} 
      />

      <main className="dashboard">

        {/* Desktop View - Always visible on desktop */}
        <div className="desktop-view">
          {/* ── ROW 1: Spot Cards strip ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '6px', flexShrink: 0 }}>
            <SpotCard label="NIFTY 50" value={marketData?.nifty?.spot} change={marketData?.nifty?.change} pointsChange={marketData?.nifty?.points_change} delay={1} />
            <SpotCard label="SENSEX" value={marketData?.sensex?.spot} change={marketData?.sensex?.change} pointsChange={marketData?.sensex?.points_change} delay={2} />
            <SpotCard label="INDIA VIX" value={marketData?.vix?.value} change={marketData?.vix?.change} pointsChange={marketData?.vix?.points_change} suffix="" delay={3} />
            <SpotCard label="GIFT NIFTY" value={marketData?.gift_nifty?.value} change={marketData?.gift_nifty?.change} pointsChange={marketData?.gift_nifty?.points_change} delay={4} />
            <SpotCard label="DTE" niftyDte={marketData?.nifty?.dte} sensexDte={marketData?.sensex?.dte} isDte delay={5} />
          </div>

          {/* ── ROW 2: Key Levels thin strip ── */}
          <div className="card fade-in" style={{ flexShrink: 0, padding: '4px 10px' }}>
            <KeyLevels niftyData={marketData?.nifty} sensexData={marketData?.sensex} />
          </div>

          {/* ── ROW 3: Main 3-column grid (fills remaining height) ── */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: '6px',
            flex: 1,
            minHeight: 0
          }}>

            {/* Col 1: NIFTY Straddle + SENSEX Straddle stacked */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minHeight: 0 }}>
              <div className="card fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <div className="card-header" style={{ marginBottom: '2px', flexShrink: 0 }}>
                  <span className="card-title">NIFTY Straddle Premium</span>
                  <span style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#2563eb' }}>
                    {marketData?.nifty?.straddle_premium ? Math.round(marketData.nifty.straddle_premium) : '—'}
                  </span>
                </div>
                <div style={{ flex: 1, minHeight: 0 }}>
                  <StraddleChart
                    data={straddleHistory['NIFTY']}
                    currentPremium={marketData?.nifty?.straddle_premium}
                    index="NIFTY"
                  />
                </div>
              </div>

              <div className="card fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <div className="card-header" style={{ marginBottom: '2px', flexShrink: 0 }}>
                  <span className="card-title">SENSEX Straddle Premium</span>
                  <span style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#2563eb' }}>
                    {marketData?.sensex?.straddle_premium ? Math.round(marketData.sensex.straddle_premium) : '—'}
                  </span>
                </div>
                <div style={{ flex: 1, minHeight: 0 }}>
                  <StraddleChart
                    data={straddleHistory['SENSEX']}
                    currentPremium={marketData?.sensex?.straddle_premium}
                    index="SENSEX"
                  />
                </div>
              </div>
            </div>

            {/* Col 2: OI Buildup (top) + OI Heatmap (bottom) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minHeight: 0 }}>

              {/* OI Buildup — 50% */}
              <div className="card fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
                <div className="card-header" style={{ marginBottom: '4px', flexShrink: 0 }}>
                  <span className="card-title">OI Buildup</span>
                  <div className="tab-switcher">
                    <button className={`tab-btn ${selectedIndex === 'NIFTY' ? 'active' : ''}`} onClick={() => setSelectedIndex('NIFTY')}>NIFTY</button>
                    <button className={`tab-btn ${selectedIndex === 'SENSEX' ? 'active' : ''}`} onClick={() => setSelectedIndex('SENSEX')}>SENSEX</button>
                  </div>
                </div>
                <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                  <OIBuildupPanel index={selectedIndex} />
                </div>
              </div>

              {/* OI Heatmap — 50% */}
              <div className="card fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
                <div className="card-header" style={{ marginBottom: '2px', flexShrink: 0 }}>
                  <span className="card-title">OI Heatmap</span>
                  <div className="tab-switcher">
                    <button className={`tab-btn ${selectedIndex === 'NIFTY' ? 'active' : ''}`} onClick={() => setSelectedIndex('NIFTY')}>NIFTY</button>
                    <button className={`tab-btn ${selectedIndex === 'SENSEX' ? 'active' : ''}`} onClick={() => setSelectedIndex('SENSEX')}>SENSEX</button>
                  </div>
                </div>
                <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                  <OIHeatmap
                    chain={optionChain[selectedIndex]}
                    atmStrike={idxData?.atm_strike}
                  />
                </div>
              </div>

            </div>

            {/* Col 3: Positions Panel */}
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, minWidth: 0 }}>
              <Positions 
                isConfigured={isConfigured} 
                onLoginClick={() => setShowLoginModal(true)} 
                marketData={marketData}
                optionChain={optionChain}
              />
            </div>

          </div>
        </div>

        {/* Mobile View - Only visible on mobile */}
        <div className="mobile-view">
          
          {/* Home Page */}
          {mobileView === 'home' && (
            <div className="mobile-page">
              {/* Spot Cards - Compact 2x2 grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', marginBottom: '6px' }}>
                <SpotCard label="NIFTY 50" value={marketData?.nifty?.spot} change={marketData?.nifty?.change} pointsChange={marketData?.nifty?.points_change} delay={1} />
                <SpotCard label="SENSEX" value={marketData?.sensex?.spot} change={marketData?.sensex?.change} pointsChange={marketData?.sensex?.points_change} delay={2} />
                <SpotCard label="INDIA VIX" value={marketData?.vix?.value} change={marketData?.vix?.change} pointsChange={marketData?.vix?.points_change} suffix="" delay={3} />
                <SpotCard label="GIFT NIFTY" value={marketData?.gift_nifty?.value} change={marketData?.gift_nifty?.change} pointsChange={marketData?.gift_nifty?.points_change} delay={4} />
              </div>

              {/* Positions - Visible without scrolling */}
              <Positions 
                isConfigured={isConfigured} 
                onLoginClick={() => setShowLoginModal(true)} 
                marketData={marketData}
                optionChain={optionChain}
              />
            </div>
          )}

          {/* Levels Page */}
          {mobileView === 'levels' && (
            <div className="mobile-page">
              {/* Key Levels */}
              <div className="card" style={{ padding: '10px', marginBottom: '12px' }}>
                <KeyLevels niftyData={marketData?.nifty} sensexData={marketData?.sensex} />
              </div>
            </div>
          )}

          {/* Straddle Page */}
          {mobileView === 'straddle' && (
            <div className="mobile-page">
              {/* Index Switcher */}
              <div className="tab-switcher" style={{ marginBottom: '12px', justifyContent: 'center' }}>
                <button className={`tab-btn ${selectedIndex === 'NIFTY' ? 'active' : ''}`} onClick={() => setSelectedIndex('NIFTY')}>NIFTY</button>
                <button className={`tab-btn ${selectedIndex === 'SENSEX' ? 'active' : ''}`} onClick={() => setSelectedIndex('SENSEX')}>SENSEX</button>
              </div>

              {/* NIFTY Straddle */}
              <div className="card" style={{ marginBottom: '12px', padding: '10px', minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
                <div className="card-header" style={{ marginBottom: '8px' }}>
                  <span className="card-title">NIFTY Straddle Premium</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#2563eb' }}>
                    {marketData?.nifty?.straddle_premium ? Math.round(marketData.nifty.straddle_premium) : '—'}
                  </span>
                </div>
                <div style={{ flex: 1, minHeight: 0 }}>
                  <StraddleChart
                    data={straddleHistory['NIFTY']}
                    currentPremium={marketData?.nifty?.straddle_premium}
                    index="NIFTY"
                  />
                </div>
              </div>

              {/* SENSEX Straddle */}
              <div className="card" style={{ padding: '10px', minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
                <div className="card-header" style={{ marginBottom: '8px' }}>
                  <span className="card-title">SENSEX Straddle Premium</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#2563eb' }}>
                    {marketData?.sensex?.straddle_premium ? Math.round(marketData.sensex.straddle_premium) : '—'}
                  </span>
                </div>
                <div style={{ flex: 1, minHeight: 0 }}>
                  <StraddleChart
                    data={straddleHistory['SENSEX']}
                    currentPremium={marketData?.sensex?.straddle_premium}
                    index="SENSEX"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Chain (Heatmap) Page */}
          {mobileView === 'chain' && (
            <div className="mobile-page">
              {/* Index Switcher */}
              <div className="tab-switcher" style={{ marginBottom: '12px', justifyContent: 'center' }}>
                <button className={`tab-btn ${selectedIndex === 'NIFTY' ? 'active' : ''}`} onClick={() => setSelectedIndex('NIFTY')}>NIFTY</button>
                <button className={`tab-btn ${selectedIndex === 'SENSEX' ? 'active' : ''}`} onClick={() => setSelectedIndex('SENSEX')}>SENSEX</button>
              </div>

              {/* OI Heatmap */}
              <div className="card" style={{ padding: '10px', minHeight: '400px', display: 'flex', flexDirection: 'column' }}>
                <div className="card-header" style={{ marginBottom: '8px' }}>
                  <span className="card-title">OI Heatmap</span>
                </div>
                <div style={{ flex: 1, overflow: 'auto' }}>
                  <OIHeatmap
                    chain={optionChain[selectedIndex]}
                    atmStrike={idxData?.atm_strike}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Buildup Page */}
          {mobileView === 'buildup' && (
            <div className="mobile-page">
              {/* Index Switcher */}
              <div className="tab-switcher" style={{ marginBottom: '12px', justifyContent: 'center' }}>
                <button className={`tab-btn ${selectedIndex === 'NIFTY' ? 'active' : ''}`} onClick={() => setSelectedIndex('NIFTY')}>NIFTY</button>
                <button className={`tab-btn ${selectedIndex === 'SENSEX' ? 'active' : ''}`} onClick={() => setSelectedIndex('SENSEX')}>SENSEX</button>
              </div>

              {/* OI Buildup */}
              <div className="card" style={{ padding: '10px', minHeight: '500px', display: 'flex', flexDirection: 'column' }}>
                <div className="card-header" style={{ marginBottom: '8px' }}>
                  <span className="card-title">OI Buildup</span>
                </div>
                <div style={{ flex: 1, overflow: 'auto' }}>
                  <OIBuildupPanel index={selectedIndex} />
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Mobile Bottom Navigation */}
        <nav className="mobile-nav">
          <button 
            className={`mobile-nav-btn ${mobileView === 'home' ? 'active' : ''}`}
            onClick={() => setMobileView('home')}
          >
            <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            <span className="mobile-nav-label">Home</span>
          </button>
          <button 
            className={`mobile-nav-btn ${mobileView === 'levels' ? 'active' : ''}`}
            onClick={() => setMobileView('levels')}
          >
            <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
              <circle cx="6" cy="6" r="1.5" fill="currentColor"/>
              <circle cx="6" cy="12" r="1.5" fill="currentColor"/>
              <circle cx="6" cy="18" r="1.5" fill="currentColor"/>
            </svg>
            <span className="mobile-nav-label">Levels</span>
          </button>
          <button 
            className={`mobile-nav-btn ${mobileView === 'straddle' ? 'active' : ''}`}
            onClick={() => setMobileView('straddle')}
          >
            <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <span className="mobile-nav-label">Straddle</span>
          </button>
          <button 
            className={`mobile-nav-btn ${mobileView === 'chain' ? 'active' : ''}`}
            onClick={() => setMobileView('chain')}
          >
            <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"/>
              <rect x="14" y="3" width="7" height="7"/>
              <rect x="14" y="14" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/>
            </svg>
            <span className="mobile-nav-label">Chain</span>
          </button>
          <button 
            className={`mobile-nav-btn ${mobileView === 'buildup' ? 'active' : ''}`}
            onClick={() => setMobileView('buildup')}
          >
            <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="20" x2="12" y2="10"/>
              <line x1="18" y1="20" x2="18" y2="4"/>
              <line x1="6" y1="20" x2="6" y2="16"/>
            </svg>
            <span className="mobile-nav-label">Buildup</span>
          </button>
        </nav>

      </main>
    </div>
  )
}

export default App
