import { useMemo, memo } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const formatOI = (oi) => {
  if (oi === null || oi === undefined) return '0'
  if (oi >= 1e7) return `${(oi / 1e7).toFixed(2)}Cr`
  if (oi >= 1e5) return `${(oi / 1e5).toFixed(1)}L`
  if (oi >= 1e3) return `${(oi / 1e3).toFixed(0)}K`
  return oi.toString()
}

const OIHeatmap = memo(function OIHeatmap({ chain, atmStrike }) {
  const chartData = useMemo(() => {
    if (!chain || chain.length === 0) return null

    // Show ±10 strikes around ATM
    const atm = atmStrike || chain[Math.floor(chain.length / 2)]?.strike
    const filtered = chain.filter(item => {
      const distance = Math.abs(item.strike - atm)
      const strikeGap = chain.length > 1 ? Math.abs(chain[1].strike - chain[0].strike) : 50
      return distance <= strikeGap * 10
    })

    const labels = filtered.map(d => d.strike.toString())
    
    // We pass ATM to chart options via a hack or directly use it in options
    return {
      labels,
      atmStrike: atm,
      datasets: [
        {
          label: 'Call OI',
          data: filtered.map(d => d.call_oi || 0),
          backgroundColor: 'rgba(239, 68, 68, 0.85)',
          borderColor: 'rgba(239, 68, 68, 1)',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.85,
          categoryPercentage: 0.9,
          hoverBackgroundColor: 'rgba(239, 68, 68, 1)',
        },
        {
          label: 'Put OI',
          data: filtered.map(d => d.put_oi || 0),
          backgroundColor: 'rgba(16, 185, 129, 0.85)',
          borderColor: 'rgba(16, 185, 129, 1)',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.85,
          categoryPercentage: 0.9,
          hoverBackgroundColor: 'rgba(16, 185, 129, 1)',
        }
      ]
    }
  }, [chain, atmStrike])

  if (!chartData) {
    return (
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
        Loading option chain...
      </div>
    )
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    layout: {
      padding: { top: 2, bottom: 2, left: 0, right: 2 }
    },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'top',
        align: 'center',
        labels: {
          usePointStyle: true,
          pointStyle: 'rect',
          boxWidth: 6,
          boxHeight: 6,
          padding: 6,
          font: { family: "'Inter', sans-serif", size: 9, weight: '600' }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        titleFont: { family: "'Inter', sans-serif", size: 11, weight: '700' },
        bodyFont: { family: "'Inter', sans-serif", size: 11, weight: '500' },
        padding: 7,
        cornerRadius: 4,
        callbacks: {
          title: (ctx) => `Strike: ${ctx[0].label}`,
          label: (ctx) => `${ctx.dataset.label}: ${formatOI(ctx.parsed.y)}`
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
        ticks: {
          maxTicksLimit: 4,
          font: { family: "'Inter', sans-serif", size: 9 },
          color: '#94a3b8',
          callback: (v) => formatOI(v)
        },
        border: { display: false }
      },
      x: {
        grid: { display: false, drawBorder: false },
        ticks: {
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 12,
          font: { family: "'Inter', sans-serif", size: 9, weight: '600' },
          color: (ctx) => parseInt(ctx.tick.label) === chartData.atmStrike ? '#2563eb' : '#64748b',
          callback: function(val) { return this.getLabelForValue(val) }
        },
        border: { display: false }
      }
    }
  }

  return (
    <div style={{ height: '100%', width: '100%', padding: '0 2px' }}>
      <Bar data={chartData} options={options} />
    </div>
  )
})

export default OIHeatmap
