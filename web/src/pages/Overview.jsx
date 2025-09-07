import { useState, useEffect } from 'react';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
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
import { apiService } from '../services/api';
import JellyfinStats from '../components/JellyfinStats';
import { Icon } from '../components/FontAwesomeIcon';
import logger from '../services/logger';

// Register Chart.js components
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

const Overview = () => {
  logger.info('[COMPONENT] Overview: Starting component initialization');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [recentNotifications, setRecentNotifications] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  
  logger.debug('[COMPONENT] Overview: State hooks initialized');

  const fetchData = async () => {
    logger.debug('Overview: Starting fetchData', { 
      currentState: { loading, hasStats: !!stats, hasHealth: !!health, hasError: !!error }
    });
    
    try {
      setRefreshing(true);
      logger.debug('Overview: Making API calls to /api/overview and /api/health');
      
      const [overviewData, healthData] = await Promise.all([
        apiService.getOverview(),
        apiService.healthCheck(),
      ]);

      logger.info('Overview: API responses received', {
        overviewStatus: overviewData.status,
        healthStatus: healthData.status,
        hasOverviewData: !!overviewData.data,
        hasHealthData: !!healthData.data,
        overviewKeys: overviewData.data ? Object.keys(overviewData.data) : [],
        healthKeys: healthData.data ? Object.keys(healthData.data) : []
      });

      // Extract data from axios response
      const overview = overviewData.data;
      logger.debug('Overview: Processing overview data', {
        hasData: !!overview,
        keys: overview ? Object.keys(overview) : [],
        totalItems: overview?.total_items,
        itemsToday: overview?.items_today
      });
      setStats(overview);
      
      logger.debug('Overview: Processing health data', {
        status: healthData.data?.status,
        components: healthData.data?.components ? Object.keys(healthData.data.components) : []
      });
      setHealth(healthData.data);
      
      const notifications = overview && overview['recent_notifications'] ? overview['recent_notifications'] : [];
      logger.debug('Overview: Processing notifications', {
        count: notifications.length,
        hasNotifications: notifications.length > 0
      });
      setRecentNotifications(notifications);
      
      setError(null);
      logger.info('Overview: Data fetch successful');
    } catch (err) {
      logger.error('Overview: API Error', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        statusText: err.response?.statusText,
        url: err.config?.url
      });
      setError('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
      logger.debug('Overview: Fetch complete, loading set to false');
    }
  };

  useEffect(() => {
    void fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100';
      case 'unhealthy':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy':
        return 'circle-check';
      case 'degraded':
        return 'triangle-exclamation';
      case 'unhealthy':
        return 'circle-xmark';
      default:
        return 'server';
    }
  };

  const getContentIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'movie':
        return 'film';
      case 'series':
      case 'episode':
        return 'tv';
      case 'music':
      case 'audio':
        return 'music';
      default:
        return 'folder';
    }
  };

  // Process historical stats for line chart
  const historicalData = stats?.historical_stats?.hourly || [];
  const lineChartData = {
    labels: historicalData.map(h => {
      const date = new Date(h.hour);
      return date.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
    }).reverse(),
    datasets: [
      {
        label: 'Webhooks Received',
        data: historicalData.map(h => h.webhooks_received || 0).reverse(),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.3,
      },
      {
        label: 'Notifications Sent',
        data: historicalData.map(h => h.sent || 0).reverse(),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        tension: 0.3,
      },
      {
        label: 'Failed',
        data: historicalData.map(h => (h.webhooks_failed || 0) + (h.failed || 0)).reverse(),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.3,
      }
    ],
  };

  // Content type distribution
  const contentStats = stats?.historical_stats?.totals || {};
  const contentTypeChartData = {
    labels: ['Movies', 'TV Shows', 'Episodes', 'Music'],
    datasets: [
      {
        data: [
          contentStats.total_movies || 0,
          contentStats.total_tv_shows || 0,
          contentStats.total_episodes || 0,
          contentStats.total_music || 0,
        ],
        backgroundColor: [
          'rgba(147, 51, 234, 0.8)',
          'rgba(59, 130, 246, 0.8)',
          'rgba(14, 165, 233, 0.8)',
          'rgba(16, 185, 129, 0.8)',
        ],
        borderWidth: 0,
      },
    ],
  };

  // Channel routing distribution
  const channelRouting = stats?.channel_routing || {};
  const channelChartData = {
    labels: ['Default', 'Movies', 'TV', 'Music'],
    datasets: [
      {
        label: 'Messages Sent',
        data: [
          channelRouting.default || 0,
          channelRouting.movies || 0,
          channelRouting.tv || 0,
          channelRouting.music || 0,
        ],
        backgroundColor: 'rgba(147, 51, 234, 0.8)',
      },
    ],
  };

  // Filtering effectiveness over time (stacked area chart)
  const filteringTrendData = {
    labels: historicalData.map(h => {
      const date = new Date(h.hour);
      return date.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
    }).reverse(),
    datasets: [
      {
        label: 'Renames Filtered',
        data: historicalData.map(h => h.renames_filtered || 0).reverse(),
        backgroundColor: 'rgba(251, 191, 36, 0.6)',
        borderColor: 'rgb(251, 191, 36)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Deletes Filtered',
        data: historicalData.map(h => h.deletes_filtered || 0).reverse(),
        backgroundColor: 'rgba(239, 68, 68, 0.6)',
        borderColor: 'rgb(239, 68, 68)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Mass Renames',
        data: historicalData.map(h => h.mass_renames || 0).reverse(),
        backgroundColor: 'rgba(168, 85, 247, 0.6)',
        borderColor: 'rgb(168, 85, 247)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Metadata Only',
        data: historicalData.map(h => h.metadata_only || 0).reverse(),
        backgroundColor: 'rgba(59, 130, 246, 0.6)',
        borderColor: 'rgb(59, 130, 246)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          display: true,
          color: 'rgba(156, 163, 175, 0.1)',
        },
      },
      x: {
        grid: {
          display: false,
        },
      },
    },
  };

  // Special options for stacked area chart
  const stackedAreaOptions = {
    ...chartOptions,
    scales: {
      ...chartOptions.scales,
      y: {
        ...chartOptions.scales.y,
        stacked: true,
      },
      x: {
        ...chartOptions.scales.x,
      },
    },
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      ...chartOptions.plugins,
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          padding: 10,
          font: {
            size: 11,
          },
        },
      },
    },
  };

  // Log render conditions
  logger.debug('Overview: Render check', {
    loading,
    hasStats: !!stats,
    hasHealth: !!health,
    hasError: !!error,
    statsKeys: stats ? Object.keys(stats) : null,
    willShowLoading: loading && !stats,
    willShowContent: !loading || stats
  });

  if (loading && !stats) {
    logger.debug('Overview: Showing loading spinner');
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  logger.info('Overview: Rendering main content', {
    statsAvailable: !!stats,
    healthAvailable: !!health,
    notificationsCount: recentNotifications.length
  });

  // Helper function to format numbers
  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num?.toString() || '0';
  };

  return (
    <div className="-mx-4 sm:-mx-6 lg:-mx-8">
      <div className="px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center pt-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard Overview</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor your Jellynouncer service health and statistics
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={refreshing}
          className={`
            inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md
            text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 
            focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          <Icon icon="arrows-rotate" className={`mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Webhook & Notification Statistics */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <Icon icon="webhook" className="mr-2" />
          Webhook & Notification Activity
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="flex-shrink-0 p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Icon icon="download" className="text-blue-600 dark:text-blue-300" size="lg" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Webhooks Received
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatNumber(stats?.webhook_stats?.received || 0)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatNumber(stats?.webhook_stats?.processed || 0)} processed
                  </p>
                </div>
              </div>
              {/* Circular progress indicator */}
              <div className="relative">
                <svg className="w-12 h-12 transform -rotate-90">
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                    className="text-gray-200 dark:text-gray-700"
                  />
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                    strokeDasharray={`${(stats?.webhook_stats?.processing_rate || 0) * 1.26} 126`}
                    className="text-blue-600 dark:text-blue-400"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold text-gray-900 dark:text-white">
                    {Math.round(stats?.webhook_stats?.processing_rate || 0)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="flex-shrink-0 p-3 bg-green-100 dark:bg-green-900 rounded-lg">
                  <Icon icon="paper-plane" className="text-green-600 dark:text-green-300" size="lg" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Notifications Sent
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatNumber(stats?.notification_stats?.sent || 0)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatNumber(stats?.notification_stats?.failed || 0)} failed
                  </p>
                </div>
              </div>
              {/* Circular progress indicator */}
              <div className="relative">
                <svg className="w-12 h-12 transform -rotate-90">
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                    className="text-gray-200 dark:text-gray-700"
                  />
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                    strokeDasharray={`${(stats?.notification_stats?.success_rate || 0) * 1.26} 126`}
                    className="text-green-600 dark:text-green-400"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold text-gray-900 dark:text-white">
                    {Math.round(stats?.notification_stats?.success_rate || 0)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0 p-3 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                <Icon icon="filter" className="text-yellow-600 dark:text-yellow-300" size="lg" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Events Filtered
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(
                    (stats?.filtering_stats?.renames_filtered || 0) +
                    (stats?.filtering_stats?.deletes_filtered || 0) +
                    (stats?.filtering_stats?.mass_renames_caught || 0)
                  )}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Spam prevented
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0 p-3 bg-red-100 dark:bg-red-900 rounded-lg">
                <Icon icon="circle-xmark" className="text-red-600 dark:text-red-300" size="lg" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Failed Events
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(
                    (stats?.webhook_stats?.failed || 0) +
                    (stats?.notification_stats?.failed || 0)
                  )}
                </p>
                <p className="text-xs text-red-600 dark:text-red-400">
                  Needs attention
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Synced Items & Jellyfin Comparison */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <Icon icon="database" className="mr-2" />
          Library Synchronization
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Jellyfin Library
                </p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(stats?.jellyfin_stats?.total_items || 0)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <Icon icon="film" className="mr-1" size="xs" />
                  {stats?.jellyfin_stats?.movie_count || 0} Movies
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  <Icon icon="tv" className="mr-1" size="xs" />
                  {stats?.jellyfin_stats?.episode_count || 0} Episodes
                </p>
              </div>
              <Icon icon="server" className="text-purple-500" size="2x" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Synced Items
                </p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(stats?.synced_items?.total || 0)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Database: {stats?.synced_items?.database_size_mb || 0} MB
                </p>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-purple-600 h-2 rounded-full"
                      style={{
                        width: `${Math.min(
                          ((stats?.synced_items?.total || 0) / Math.max(stats?.jellyfin_stats?.total_items || 1, 1)) * 100,
                          100
                        )}%`
                      }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {Math.round(
                      ((stats?.synced_items?.total || 0) / Math.max(stats?.jellyfin_stats?.total_items || 1, 1)) * 100
                    )}% coverage
                  </p>
                </div>
              </div>
              <Icon icon="hard-drive" className="text-blue-500" size="2x" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Content Processed
                </p>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">
                      <Icon icon="plus" className="mr-1" size="xs" />
                      New
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {stats?.historical_stats?.totals?.total_new || 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">
                      <Icon icon="arrow-up" className="mr-1" size="xs" />
                      Upgraded
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {stats?.historical_stats?.totals?.total_upgraded || 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">
                      <Icon icon="trash" className="mr-1" size="xs" />
                      Deleted
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {stats?.historical_stats?.totals?.total_deleted || 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">
                      <Icon icon="code" className="mr-1" size="xs" />
                      Metadata
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {stats?.filtering_stats?.metadata_only || 0}
                    </span>
                  </div>
                </div>
              </div>
              <Icon icon="chart-line" className="text-green-500" size="2x" />
            </div>
          </div>
        </div>
      </div>

      {/* Health Status Cards */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <Icon icon="heart-pulse" className="mr-2" />
          System Health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {health && health['components'] && Object.entries(health['components']).map(([name, status]) => (
            <div key={name} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400 capitalize">
                    {name.replace('_', ' ')}
                  </p>
                  <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white capitalize">
                    {status}
                  </p>
                </div>
                <div className={`p-2 rounded-full ${getHealthColor(status)}`}>
                  <Icon icon={getHealthIcon(status)} size="lg" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            <Icon icon="chart-line" className="mr-2" />
            Activity Over Time (24 Hours)
          </h2>
          <div className="h-64">
            <Line data={lineChartData} options={chartOptions} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            <Icon icon="chart-pie" className="mr-2" />
            Content Distribution
          </h2>
          <div className="h-64">
            <Doughnut data={contentTypeChartData} options={{ ...chartOptions, aspectRatio: 1 }} />
          </div>
        </div>
      </div>

      {/* Filtering Trends Over Time */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <Icon icon="filter" className="mr-2" />
          Filtering Trends (24 Hours)
        </h2>
        <div className="h-64">
          <Line data={filteringTrendData} options={stackedAreaOptions} />
        </div>
      </div>

      {/* Channel Routing and Success Rates */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            <Icon icon="hashtag" className="mr-2" />
            Discord Channel Routing
          </h2>
          <div className="h-48">
            <Bar data={channelChartData} options={chartOptions} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            <Icon icon="shield-halved" className="mr-2" />
            Filtering Effectiveness Summary
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                <Icon icon="file-pen" className="mr-2" size="sm" />
                Renames Filtered
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {stats?.filtering_stats?.renames_filtered || 0}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                <Icon icon="trash-can" className="mr-2" size="sm" />
                Deletes Filtered
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {stats?.filtering_stats?.deletes_filtered || 0}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                <Icon icon="layer-group" className="mr-2" size="sm" />
                Mass Renames Caught
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {stats?.filtering_stats?.mass_renames_caught || 0}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                <Icon icon="code-branch" className="mr-2" size="sm" />
                Metadata-Only Updates
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {stats?.filtering_stats?.metadata_only || 0}
              </span>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Total Spam Prevented
                </span>
                <span className="text-xl font-bold text-green-600 dark:text-green-400">
                  {formatNumber(
                    (stats?.filtering_stats?.renames_filtered || 0) +
                    (stats?.filtering_stats?.deletes_filtered || 0) +
                    (stats?.filtering_stats?.mass_renames_caught || 0) +
                    (stats?.filtering_stats?.metadata_only || 0)
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Jellyfin Server Statistics */}
      {stats && stats['jellyfin_stats'] && (
        <JellyfinStats stats={stats['jellyfin_stats']} />
      )}

      {/* System Performance */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <Icon icon="gauge-high" className="mr-2" />
          System Performance
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.system_health?.cpu_usage || 0}%
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">CPU Usage</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.system_health?.memory_usage || 0}%
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Memory Usage</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.system_health?.disk_usage || 0}%
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Disk Usage</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.system_health?.uptime_hours || 0}h
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Uptime</p>
          </div>
        </div>
      </div>

      {/* Recent Notifications */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            <Icon icon="bell" className="mr-2" />
            Recent Notifications
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Event
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {recentNotifications.length > 0 ? (
                recentNotifications.map((notification, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      {new Date(notification.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900 dark:text-gray-300">
                        <Icon icon={getContentIcon(notification.type)} className="mr-2" size="sm" />
                        <span>{notification.type}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      {notification.title || notification.name || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      <span className={`
                        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${notification.event === 'new' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                          notification.event === 'upgraded' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                          notification.event === 'deleted' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                          'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}
                      `}>
                        {notification.event || notification.last_event || 'unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      <span className={`
                        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${notification.status === 'sent' || notification.status === 'success' ? 
                          'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                          notification.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                          'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}
                      `}>
                        {notification.status || 'pending'}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    No recent notifications
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      </div>
    </div>
  );
};

export default Overview;