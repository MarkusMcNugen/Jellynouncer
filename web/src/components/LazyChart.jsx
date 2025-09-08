import { lazy, Suspense } from 'react';

// Lazy load Chart.js components
const Line = lazy(() => import('react-chartjs-2').then(module => ({ default: module.Line })));
const Doughnut = lazy(() => import('react-chartjs-2').then(module => ({ default: module.Doughnut })));
const Bar = lazy(() => import('react-chartjs-2').then(module => ({ default: module.Bar })));

// Loading placeholder for charts
const ChartLoading = () => (
  <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg">
    <div className="text-gray-500 dark:text-gray-400">Loading chart...</div>
  </div>
);

// Wrapper components with Suspense
export const LazyLine = (props) => (
  <Suspense fallback={<ChartLoading />}>
    <Line {...props} />
  </Suspense>
);

export const LazyDoughnut = (props) => (
  <Suspense fallback={<ChartLoading />}>
    <Doughnut {...props} />
  </Suspense>
);

export const LazyBar = (props) => (
  <Suspense fallback={<ChartLoading />}>
    <Bar {...props} />
  </Suspense>
);

// Also lazy load the Chart.js registration
export const registerChartJS = async () => {
  const ChartJS = await import('chart.js').then(m => m.Chart);
  const modules = await Promise.all([
    import('chart.js').then(m => m.CategoryScale),
    import('chart.js').then(m => m.LinearScale),
    import('chart.js').then(m => m.PointElement),
    import('chart.js').then(m => m.LineElement),
    import('chart.js').then(m => m.BarElement),
    import('chart.js').then(m => m.ArcElement),
    import('chart.js').then(m => m.Title),
    import('chart.js').then(m => m.Tooltip),
    import('chart.js').then(m => m.Legend),
    import('chart.js').then(m => m.Filler),
  ]);
  
  ChartJS.register(...modules);
};