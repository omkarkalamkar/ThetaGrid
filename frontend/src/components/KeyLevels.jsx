import { memo } from 'react'

const KeyLevels = memo(function KeyLevels({ niftyData, sensexData }) {
  if (!niftyData || !sensexData) {
    return (
      <div className="key-levels-horizontal">
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px', width: '100%' }}>
          Waiting for data...
        </div>
      </div>
    )
  }

  const formatValue = (data, key, type) => {
    if (!data) return { value: '—', className: '' }
    
    switch (type) {
      case 'strike':
        return { value: data[key]?.toLocaleString('en-IN'), className: 'accent' }
      case 'iv':
        return { 
          value: `${data[key]}%`, 
          className: data[key] > 20 ? 'negative' : 'positive' 
        }
      case 'expected_move':
        return { value: `±${Math.round(data[key])?.toLocaleString('en-IN')} pts`, className: 'amber' }
      case 'expected_range':
        return { 
          value: data[key] ? `${Math.round(data[key][0])?.toLocaleString('en-IN')} - ${Math.round(data[key][1])?.toLocaleString('en-IN')}` : '—',
          className: 'purple'
        }
      case 'pcr':
        return {
          value: data[key]?.toString(),
          className: data[key] > 1.2 ? 'positive' : data[key] < 0.8 ? 'negative' : ''
        }
      case 'oi_support':
        return {
          value: data.oi_support?.strike?.toLocaleString('en-IN'),
          className: 'positive'
        }
      case 'oi_resistance':
        return {
          value: data.oi_resistance?.strike?.toLocaleString('en-IN'),
          className: 'negative'
        }
      default:
        return { value: '—', className: '' }
    }
  }

  const rowConfig = [
    { label: 'ATM Strike', key: 'atm_strike', type: 'strike' },
    { label: 'ATM IV', key: 'atm_iv', type: 'iv' },
    { label: 'Expected Move', key: 'expected_move', type: 'expected_move' },
    { label: 'Expected Range', key: 'expected_range', type: 'expected_range' },
    { label: 'PCR (OI)', key: 'pcr', type: 'pcr' },
    { label: 'Max Pain', key: 'max_pain', type: 'strike' },
    { label: 'OI Support', key: 'oi_support', type: 'oi_support' },
    { label: 'OI Resistance', key: 'oi_resistance', type: 'oi_resistance' },
  ]

  return (
    <div className="key-levels-horizontal">
      {rowConfig.map((col, i) => {
        const nData = formatValue(niftyData, col.key, col.type)
        const sData = formatValue(sensexData, col.key, col.type)
        
        return (
          <div className={`key-level-block block-${col.key}`} key={i}>
            <div className="block-title">{col.label}</div>
            <div className="block-content">
              <div className="block-row">
                <span className="idx-label">NIFTY</span>
                <span className={`idx-value ${nData.className}`}>
                  {nData.value}
                </span>
              </div>
              <div className="block-row">
                <span className="idx-label">SENSEX</span>
                <span className={`idx-value ${sData.className}`}>
                  {sData.value}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
})

export default KeyLevels
