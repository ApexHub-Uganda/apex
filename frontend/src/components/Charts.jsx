import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { useTheme } from '../hooks/useTheme';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const getChartColors = (isDark) => ({
  primary: '#0F766E',
  secondary: '#FF7F50',
  accent: '#14B8A6',
  grid: isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(226, 232, 240, 0.8)',
  text: isDark ? '#94A3B8' : '#64748B',
});

export function useChartOptions(overrides = {}) {
  const { isDark } = useTheme();
  const colors = getChartColors(isDark);

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: colors.text, usePointStyle: true, padding: 16 },
      },
      tooltip: {
        backgroundColor: isDark ? '#1E293B' : '#FFFFFF',
        titleColor: isDark ? '#F1F5F9' : '#0F172A',
        bodyColor: isDark ? '#94A3B8' : '#64748B',
        borderColor: isDark ? '#334155' : '#E2E8F0',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: { color: colors.grid, drawBorder: false },
        ticks: { color: colors.text },
      },
      y: {
        grid: { color: colors.grid, drawBorder: false },
        ticks: { color: colors.text },
      },
    },
    ...overrides,
  };
}

export function LineChart({ data, height = 300, options: customOptions }) {
  const baseOptions = useChartOptions();
  const colors = getChartColors(false);

  const chartData = {
    labels: data?.labels || [],
    datasets: (data?.datasets || []).map((ds, i) => ({
      ...ds,
      borderColor: ds.borderColor || [colors.primary, colors.secondary, colors.accent][i % 3],
      backgroundColor: ds.backgroundColor || `rgba(15, 118, 110, ${0.1 + i * 0.05})`,
      fill: ds.fill ?? true,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    })),
  };

  return (
    <div style={{ height }}>
      <Line data={chartData} options={{ ...baseOptions, ...customOptions }} />
    </div>
  );
}

export function BarChart({ data, height = 300, options: customOptions }) {
  const baseOptions = useChartOptions();
  const colors = getChartColors(false);

  const chartData = {
    labels: data?.labels || [],
    datasets: (data?.datasets || []).map((ds, i) => ({
      ...ds,
      backgroundColor: ds.backgroundColor || [colors.primary, colors.secondary, colors.accent][i % 3],
      borderRadius: 6,
      borderSkipped: false,
    })),
  };

  return (
    <div style={{ height }}>
      <Bar data={chartData} options={{ ...baseOptions, ...customOptions }} />
    </div>
  );
}

export function DoughnutChart({ data, height = 250, options: customOptions }) {
  const baseOptions = useChartOptions({ scales: undefined });
  const colors = getChartColors(false);

  const chartData = {
    labels: data?.labels || [],
    datasets: (data?.datasets || []).map((ds) => ({
      ...ds,
      backgroundColor: ds.backgroundColor || [colors.primary, colors.secondary, colors.accent, '#F5E6CA'],
      borderWidth: 0,
      hoverOffset: 8,
    })),
  };

  return (
    <div style={{ height }}>
      <Doughnut data={chartData} options={{ ...baseOptions, ...customOptions }} />
    </div>
  );
}

export default { LineChart, BarChart, DoughnutChart };