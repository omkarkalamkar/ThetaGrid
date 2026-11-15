import { useState, useEffect } from 'react'

export default function TopBar({ connected, isDemo, currentPage, setCurrentPage }) {
  const [time, setTime] = useState('')

  useEffect(() => {
    const update = () => {
      const now = new Date()
      setTime(now.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }))
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <div className="topbar-logo">θ</div>
        <div>
          <div className="topbar-title">
            ThetaGrid
            <span className="topbar-subtitle"> — Options Intelligence</span>
          </div>
        </div>
      </div>

      <div className="topbar-status">
        <div className={`status-badge ${isDemo ? 'demo' : 'live'}`}>
          <span className="status-dot"></span>
          {isDemo ? 'Demo Mode' : 'Live'}
        </div>

        <div className={`status-badge ${connected ? 'live' : 'demo'}`}>
          <span className="status-dot"></span>
          {connected ? 'Connected' : 'Disconnected'}
        </div>

        <span className="topbar-time">{time} IST</span>
      </div>
    </header>
  )
}
