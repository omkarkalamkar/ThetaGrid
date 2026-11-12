import { useRef, useEffect, useMemo } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler
)

export default function StraddleChart({ data, currentPremium, index }) {
  const chartRef = useRef(null)

  const chartData = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        labels: [],
        datasets: [{
          label: 'Straddle Premium',
          data: [],
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.08)',
          fill: true,
        }],
      }
    }

    const labels = data.map(d => d.time.substring(0, 5))
    const values = data.map(d => d.premium)
    const vwapValues = data.map(d => d.vwap || d.premium)

    return {
      labels,
      datasets: [
        {
          label: index,
          data: values,
          borderColor: '#2563eb', // Rich institutional blue for light bg
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          fill: false,
          tension: 0.1, // Less smooth, more jagged like real charts
          pointRadius: 0,
          pointHitRadius: 8,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: '#2563eb',
          pointHoverBorderColor: '#fff',
          pointHoverBorderWidth: 2,
        },
        {
          label: 'VWAP',
          data: vwapValues,
          borderColor: '#d97706', // amber
          borderDash: [4, 4],
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHitRadius: 8,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: '#d97706',
          pointHoverBorderColor: '#fff',
          pointHoverBorderWidth: 2,
        },
      ],
    }
  }, [data, index])

  // Custom plugins
  const watermarkPlugin = useMemo(() => ({
    id: 'watermark',
    beforeDraw: (chart) => {
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      ctx.save();
      ctx.font = 'bold 100px Inter, sans-serif';
      ctx.fillStyle = 'rgba(0, 0, 0, 0.03)'; // Dark watermark for light bg
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(index, (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2);
      ctx.restore();
    }
  }), [index])

  const latestPricePlugin = useMemo(() => ({
    id: 'latestPrice',
    afterDatasetsDraw: (chart) => {
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      chart.data.datasets.forEach((dataset, i) => {
        if (dataset.data.length === 0) return;
        
        const meta = chart.getDatasetMeta(i);
        const lastPoint = meta.data[meta.data.length - 1];
        if (!lastPoint) return;
        
        const value = dataset.data[dataset.data.length - 1];
        const yPos = lastPoint.y;
        const xPos = lastPoint.x;

        ctx.save();
        ctx.fillStyle = dataset.borderColor; // Use dataset color for box
        ctx.beginPath();
        // Draw rectangle, shifted slightly left so it overlaps the line end
        ctx.roundRect(xPos - 20, yPos - 10, 44, 20, 3);
        ctx.fill();
        
        ctx.fillStyle = '#ffffff'; // White text
        ctx.font = 'bold 11px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(value.toFixed(2), xPos + 2, yPos);
        ctx.restore();
      });
    }
  }), [])

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        titleColor: '#64748b',
        bodyColor: '#0f172a',
        borderColor: 'rgba(0, 0, 0, 0.1)',
        borderWidth: 1,
        cornerRadius: 8,
        padding: 10,
        bodyFont: {
          family: "'JetBrains Mono', monospace",
          size: 13,
          weight: '600',
        },
        titleFont: {
          family: "'Inter', sans-serif",
          size: 11,
        },
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ₹${ctx.parsed.y.toFixed(2)}`,
        },
        displayColors: true,
      },
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(0, 0, 0, 0.04)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          font: { family: "'Inter', sans-serif", size: 11, weight: '600' },
          maxTicksLimit: 6,
          maxRotation: 0,
          autoSkip: true,
        },
        border: { display: true, color: '#cbd5e1' },
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.04)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          font: { family: "'Inter', sans-serif", size: 10 },
          maxTicksLimit: 5,
          callback: (val) => Math.round(val),
        },
        border: { display: false },
      },
    },
    animation: {
      duration: 300,
    },
  }), [])

  return (
    <div style={{ height: '100%', width: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div className="chart-container" style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Line 
          ref={chartRef} 
          data={chartData} 
          options={options} 
          plugins={[watermarkPlugin, latestPricePlugin]}
        />
      </div>
    </div>
  )
}
