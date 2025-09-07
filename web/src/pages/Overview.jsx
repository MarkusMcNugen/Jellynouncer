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
  logger.info('[Overview] Component initialization started');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [recentNotifications, setRecentNotifications] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  
  logger.debug('[Overview] State hooks initialized', {
    initialStates: {
      loading: true,
      error: null,
      stats: null,
      health: null,
      recentNotifications: [],
      refreshing: false
    }
  });

  const fetchData = async () => {
    const fetchTimer = logger.startTimer('[Overview] fetchData execution');
    
    logger.debug('[Overview] fetchData called', { 
      currentState: { 
        loading, 
        hasStats: !!stats, 
        hasHealth: !!health, 
        hasError: !!error,
        statsKeys: stats ? Object.keys(stats) : null
      }
    });
    
    try {
      setRefreshing(true);
      logger.debug('[Overview] Starting parallel API calls');
      
      const apiTimer = logger.startTimer('[Overview] API calls');
      const [overviewData, healthData] = await Promise.all([
        apiService.getOverview(),
        apiService.healthCheck(),
      ]);
      apiTimer.end();

      logger.info('[Overview] API responses received', {
        overviewStatus: overviewData?.status,
        healthStatus: healthData?.status,
        hasOverviewData: !!overviewData?.data,
        hasHealthData: !!healthData?.data,
        overviewKeys: overviewData?.data ? Object.keys(overviewData.data) : [],
        healthKeys: healthData?.data ? Object.keys(healthData.data) : []
      });

      // Extract data from axios response
      const overview = overviewData?.data;
      
      // Deep inspection of overview data
      logger.debug('[Overview] Processing overview data - detailed inspection', {
        hasData: !!overview,
        dataType: typeof overview,
        keys: overview ? Object.keys(overview) : [],
        jellyfin_stats: {
          exists: !!overview?.jellyfin_stats,
          keys: overview?.jellyfin_stats ? Object.keys(overview.jellyfin_stats) : [],
          total_items: overview?.jellyfin_stats?.total_items,
          server_status: overview?.jellyfin_stats?.server_status
        },
        webhook_stats: {
          exists: !!overview?.webhook_stats,
          received: overview?.webhook_stats?.received,
          failed: overview?.webhook_stats?.failed
        },
        notification_stats: {
          exists: !!overview?.notification_stats,
          sent: overview?.notification_stats?.sent,
          failed: overview?.notification_stats?.failed
        },
        synced_items: {
          exists: !!overview?.synced_items,
          total: overview?.synced_items?.total,
          database_size_mb: overview?.synced_items?.database_size_mb
        },
        historical_stats: {
          exists: !!overview?.historical_stats,
          hasHourly: !!overview?.historical_stats?.hourly,
          hourlyCount: overview?.historical_stats?.hourly?.length,
          hasTotals: !!overview?.historical_stats?.totals
        }
      });
      
      setStats(overview);
      
      logger.debug('[Overview] Processing health data', {
        status: healthData?.data?.status,
        components: healthData?.data?.components ? Object.keys(healthData.data.components) : [],
        componentValues: healthData?.data?.components
      });
      setHealth(healthData?.data);
      
      const notifications = overview?.recent_notifications || [];
      logger.debug('[Overview] Processing notifications', {
        count: notifications.length,
        hasNotifications: notifications.length > 0,
        firstNotification: notifications[0] ? {
          title: notifications[0].title,
          event: notifications[0].event,
          status: notifications[0].status,
          timestamp: notifications[0].timestamp
        } : null
      });
      setRecentNotifications(notifications);
      
      setError(null);
      logger.info('[Overview] Data fetch completed successfully', {
        statsSet: !!overview,
        healthSet: !!healthData?.data,
        notificationsCount: notifications.length
      });
      
      fetchTimer.end();
    } catch (err) {
      logger.error('[Overview] API Error occurred', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        statusText: err.response?.statusText,
        url: err.config?.url,
        stack: err.stack
      });
      setError('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
      logger.debug('[Overview] Fetch complete', {
        loading: false,
        refreshing: false,
        hasError: !!error,
        hasStats: !!stats
      });
    }
  };

  useEffect(() => {
    logger.debug('[Overview] useEffect triggered - initial mount');
    void fetchData();
    
    const interval = setInterval(() => {
      logger.debug('[Overview] Auto-refresh triggered (30s interval)');
      fetchData();
    }, 30000); // Refresh every 30 seconds
    
    return () => {
      logger.debug('[Overview] Component unmounting - clearing interval');
      clearInterval(interval);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
        return 'tv';
      case 'episode':
        return 'clapperboard';  // More specific icon for episodes
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
  logger.debug('[Overview] Render decision point', {
    loading,
    hasStats: !!stats,
    hasHealth: !!health,
    hasError: !!error,
    statsKeys: stats ? Object.keys(stats) : null,
    jellyfin_stats: stats?.jellyfin_stats ? Object.keys(stats.jellyfin_stats) : null,
    willShowLoading: loading && !stats,
    willShowContent: !loading || !!stats,
    totalLibraryItems: stats?.jellyfin_stats?.total_items,
    syncedItems: stats?.synced_items?.total
  });

  if (loading && !stats) {
    logger.debug('[Overview] Rendering loading state');
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  logger.info('[Overview] Rendering main content', {
    statsAvailable: !!stats,
    healthAvailable: !!health,
    notificationsCount: recentNotifications.length,
    jellyfinStats: {
      total_items: stats?.jellyfin_stats?.total_items,
      server_name: stats?.jellyfin_stats?.server_name,
      server_status: stats?.jellyfin_stats?.server_status
    },
    webhookStats: {
      received: stats?.webhook_stats?.received,
      failed: stats?.webhook_stats?.failed
    },
    notificationStats: {
      sent: stats?.notification_stats?.sent,
      failed: stats?.notification_stats?.failed,
      success_rate: stats?.notification_stats?.success_rate
    }
  });

  // Helper function to format numbers
  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num?.toString() || '0';
  };

  return (
    <div className="-mx-4 sm:-mx-6 lg:-mx-8">
      <div className="px-4 sm:px-6 lg:px-8 space-y-8">
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

        {/* SECTION 1: Jellyfin Server Statistics */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Icon icon="server" className="mr-3 text-purple-600" size="lg" />
            Jellyfin Server
          </h2>
          
          {/* Library Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Total Library Items
                  </p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {formatNumber(stats?.jellyfin_stats?.total_items || 0)}
                  </p>
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 space-y-1">
                    <div className="flex justify-between">
                      <span><Icon icon="film" className="mr-1" size="xs" />Movies</span>
                      <span className="font-medium">{stats?.jellyfin_stats?.movie_count || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span><Icon icon="clapperboard" className="mr-1" size="xs" />Episodes</span>
                      <span className="font-medium">{stats?.jellyfin_stats?.episode_count || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span><Icon icon="music" className="mr-1" size="xs" />Music</span>
                      <span className="font-medium">{stats?.jellyfin_stats?.music_count || 0}</span>
                    </div>
                  </div>
                </div>
                <Icon icon="database" className="text-purple-500 opacity-20" size="3x" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Local Database Sync
                  </p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {formatNumber(stats?.synced_items?.total || 0)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Database: {(stats?.synced_items?.database_size_mb || 0).toFixed(1)} MB
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Last sync: {stats?.synced_items?.last_sync_time ? 
                      new Date(stats.synced_items.last_sync_time).toLocaleString() : 
                      'Never synced'}
                  </p>
                  <div className="mt-3">
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                        style={Object.assign({}, {
                          width: `${Math.min(
                            ((stats?.synced_items?.total || 0) / Math.max(stats?.jellyfin_stats?.total_items || 1, 1)) * 100,
                            100
                          )}%`
                        })}
                      />
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {Math.round(
                        ((stats?.synced_items?.total || 0) / Math.max(stats?.jellyfin_stats?.total_items || 1, 1)) * 100
                      )}% synced
                      {stats?.synced_items?.recent_additions > 0 && (
                        <span className="ml-2 text-green-500">
                          (+{stats.synced_items.recent_additions} today)
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                <Icon icon="hard-drive" className="text-blue-500 opacity-20" size="3x" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Server Status
                  </p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white capitalize mt-1">
                    {stats?.jellyfin_stats?.server_name || 'Unknown'}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Version: {stats?.jellyfin_stats?.server_version || 'Unknown'}
                  </p>
                  <div className="mt-3 flex items-center">
                    <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      stats?.jellyfin_stats?.server_status === 'online' ? 'bg-green-100 text-green-800' :
                      stats?.jellyfin_stats?.server_status === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {stats?.jellyfin_stats?.server_status || 'unknown'}
                    </div>
                  </div>
                </div>
                <Icon icon="signal" className="text-green-500 opacity-20" size="3x" />
              </div>
            </div>
          </div>

          {/* Detailed Jellyfin Stats Component */}
          {stats && stats['jellyfin_stats'] && (
            <JellyfinStats stats={stats['jellyfin_stats']} />
          )}
        </div>

        {/* SECTION 2: Processing Pipeline */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Icon icon="gears" className="mr-3 text-blue-600" size="lg" />
            Processing Pipeline
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
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
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0 p-3 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                    <Icon icon="filter" className="text-yellow-600 dark:text-yellow-300" size="lg" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Webhooks Filtered
                    </p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {formatNumber(
                        (stats?.filtering_stats?.renames_filtered || 0) +
                        (stats?.filtering_stats?.deletes_filtered || 0) +
                        (stats?.filtering_stats?.mass_renames_caught || 0)
                      )}
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
                      strokeDasharray={`${Math.min(((stats?.filtering_stats?.renames_filtered || 0) + (stats?.filtering_stats?.deletes_filtered || 0) + (stats?.filtering_stats?.mass_renames_caught || 0)) / Math.max((stats?.webhook_stats?.received || 1), 1) * 100, 100) * 1.26} 126`}
                      className="text-yellow-600 dark:text-yellow-400"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs font-bold text-gray-900 dark:text-white">
                      {Math.round(Math.min(((stats?.filtering_stats?.renames_filtered || 0) + (stats?.filtering_stats?.deletes_filtered || 0) + (stats?.filtering_stats?.mass_renames_caught || 0)) / Math.max((stats?.webhook_stats?.received || 1), 1) * 100, 100))}%
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
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0 p-3 bg-red-100 dark:bg-red-900 rounded-lg">
                    <Icon icon="circle-xmark" className="text-red-600 dark:text-red-300" size="lg" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Failed Webhooks
                    </p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {formatNumber(
                        (stats?.webhook_stats?.failed || 0) +
                        (stats?.notification_stats?.failed || 0)
                      )}
                    </p>
                  </div>
                </div>
                {/* Circular progress indicator - inverted to show failure rate */}
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
                      strokeDasharray={`${Math.min(((stats?.webhook_stats?.failed || 0) + (stats?.notification_stats?.failed || 0)) / Math.max((stats?.webhook_stats?.received || 1), 1) * 100, 100) * 1.26} 126`}
                      className="text-red-600 dark:text-red-400"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs font-bold text-gray-900 dark:text-white">
                      {Math.round(Math.min(((stats?.webhook_stats?.failed || 0) + (stats?.notification_stats?.failed || 0)) / Math.max((stats?.webhook_stats?.received || 1), 1) * 100, 100))}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Activity Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              <Icon icon="chart-line" className="mr-2" />
              Activity Over Time (24 Hours)
            </h3>
            <div className="h-64">
              <Line data={lineChartData} options={chartOptions} />
            </div>
          </div>
        </div>

        {/* SECTION 3: Content Distribution & Routing */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Icon icon="route" className="mr-3 text-green-600" size="lg" />
            Content Distribution & Discord Routing
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Content Type Distribution */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                <Icon icon="chart-pie" className="mr-2" />
                Content Types
              </h3>
              <div className="h-64">
                <Doughnut data={contentTypeChartData} options={Object.assign({}, chartOptions, { aspectRatio: 1 })} />
              </div>
            </div>

            {/* Channel Routing */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                <Icon icon="hashtag" className="mr-2" />
                Discord Channels
              </h3>
              <div className="h-64">
                <Bar data={channelChartData} options={chartOptions} />
              </div>
            </div>

            {/* Processing Stats */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                <Icon icon="list-check" className="mr-2" />
                Processing Summary
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400">New Items</span>
                    <span className="text-sm font-medium">{stats?.historical_stats?.totals?.total_new || 0}</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div className="bg-green-600 h-2 rounded-full" style={Object.assign({}, {width: '45%'})}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Upgraded</span>
                    <span className="text-sm font-medium">{stats?.historical_stats?.totals?.total_upgraded || 0}</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={Object.assign({}, {width: '30%'})}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Deleted</span>
                    <span className="text-sm font-medium">{stats?.historical_stats?.totals?.total_deleted || 0}</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div className="bg-red-600 h-2 rounded-full" style={Object.assign({}, {width: '15%'})}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Filtered</span>
                    <span className="text-sm font-medium">
                      {(stats?.filtering_stats?.renames_filtered || 0) +
                       (stats?.filtering_stats?.deletes_filtered || 0) +
                       (stats?.filtering_stats?.metadata_only || 0)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div className="bg-yellow-600 h-2 rounded-full" style={Object.assign({}, {width: '10%'})}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 4: Filtering Intelligence */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Icon icon="shield-halved" className="mr-3 text-yellow-600" size="lg" />
            Filtering Intelligence
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Filtering Trends Chart */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                <Icon icon="filter" className="mr-2" />
                Filtering Trends (24 Hours)
              </h3>
              <div className="h-64">
                <Line data={filteringTrendData} options={stackedAreaOptions} />
              </div>
            </div>

            {/* Filtering Effectiveness */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                <Icon icon="shield-check" className="mr-2" />
                Filtering Effectiveness
              </h3>
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
        </div>

        {/* SECTION 4: Recent Notifications */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Icon icon="bell" className="mr-3 text-purple-600" size="lg" />
            Recent Notifications
          </h2>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="p-6">
              {recentNotifications.length > 0 ? (
                <div className="space-y-4">
                  {recentNotifications.slice(0, 10).map((notification, index) => (
                    <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          {/* Header row with icon, title, and badges */}
                          <div className="flex items-start gap-3 mb-2">
                            <div className="flex-shrink-0 mt-1">
                              <Icon icon={getContentIcon(notification.type)} className="text-purple-600 dark:text-purple-400" size="lg" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                                  {notification.title || notification.name || 'Unknown Item'}
                                </h4>
                                <span className={`
                                  inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                  ${notification.event === 'new' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                                    notification.event === 'upgraded' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                                    notification.event === 'deleted' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                    'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}
                                `}>
                                  {notification.event || notification.last_event || 'unknown'}
                                </span>
                                <span className={`
                                  inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                  ${notification.status === 'sent' || notification.status === 'success' ? 
                                    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                                    notification.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}
                                `}>
                                  <Icon icon={notification.status === 'sent' || notification.status === 'success' ? 'circle-check' : 
                                              notification.status === 'failed' ? 'circle-xmark' : 'clock'} 
                                        className="mr-1" size="xs" />
                                  {notification.status || 'pending'}
                                </span>
                              </div>
                              
                              {/* Details */}
                              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-2 text-sm">
                                <div className="flex items-center text-gray-600 dark:text-gray-400">
                                  <Icon icon="clock" className="mr-2" size="sm" />
                                  <span>{new Date(notification.timestamp).toLocaleString()}</span>
                                </div>
                                
                                {notification.type && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="tag" className="mr-2" size="sm" />
                                    <span className="capitalize">{notification.type}</span>
                                  </div>
                                )}
                                
                                {notification.library && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="folder" className="mr-2" size="sm" />
                                    <span>{notification.library}</span>
                                  </div>
                                )}
                                
                                {notification.year && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="calendar" className="mr-2" size="sm" />
                                    <span>{notification.year}</span>
                                  </div>
                                )}
                                
                                {notification.quality && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="display" className="mr-2" size="sm" />
                                    <span>{notification.quality}</span>
                                  </div>
                                )}
                                
                                {notification.size && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="hard-drive" className="mr-2" size="sm" />
                                    <span>{notification.size}</span>
                                  </div>
                                )}
                                
                                {notification.webhook_name && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="hashtag" className="mr-2" size="sm" />
                                    <span>#{notification.webhook_name}</span>
                                  </div>
                                )}
                                
                                {notification.discord_message_id && (
                                  <div className="flex items-center text-gray-600 dark:text-gray-400">
                                    <Icon icon="message" className="mr-2" size="sm" />
                                    <span>Message sent</span>
                                  </div>
                                )}
                              </div>
                              
                              {/* Overview if available */}
                              {notification.overview && (
                                <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
                                  <p className="line-clamp-2">{notification.overview}</p>
                                </div>
                              )}
                              
                              {/* Error message if failed */}
                              {notification.status === 'failed' && notification.error_message && (
                                <div className="mt-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded p-2">
                                  <Icon icon="triangle-exclamation" className="mr-2" size="sm" />
                                  {notification.error_message}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {recentNotifications.length > 10 && (
                    <div className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2">
                      Showing 10 of {recentNotifications.length} recent notifications
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Icon icon="bell-slash" className="mx-auto text-gray-400 dark:text-gray-600 mb-4" size="3x" />
                  <p className="text-gray-500 dark:text-gray-400">No recent notifications</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                    Notifications will appear here as webhooks are processed
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SECTION 5: System Health (moved to bottom) */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <Icon icon="heart-pulse" className="mr-3 text-red-600" size="lg" />
            System Health & Performance
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Service Health Status */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Service Status</h3>
              <div className="grid grid-cols-2 gap-4">
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

            {/* System Performance Metrics */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance Metrics</h3>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600 dark:text-gray-400">CPU Usage</span>
                      <span className="text-sm font-medium">{stats?.system_health?.cpu_usage || 0}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          (stats?.system_health?.cpu_usage || 0) > 80 ? 'bg-red-600' :
                          (stats?.system_health?.cpu_usage || 0) > 60 ? 'bg-yellow-600' : 'bg-green-600'
                        }`}
                        style={Object.assign({}, {width: `${stats?.system_health?.cpu_usage || 0}%`})}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Memory</span>
                      <span className="text-sm font-medium">{stats?.system_health?.memory_usage || 0}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          (stats?.system_health?.memory_usage || 0) > 80 ? 'bg-red-600' :
                          (stats?.system_health?.memory_usage || 0) > 60 ? 'bg-yellow-600' : 'bg-green-600'
                        }`}
                        style={Object.assign({}, {width: `${stats?.system_health?.memory_usage || 0}%`})}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Disk Usage</span>
                      <span className="text-sm font-medium">{stats?.system_health?.disk_usage || 0}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          (stats?.system_health?.disk_usage || 0) > 80 ? 'bg-red-600' :
                          (stats?.system_health?.disk_usage || 0) > 60 ? 'bg-yellow-600' : 'bg-green-600'
                        }`}
                        style={Object.assign({}, {width: `${stats?.system_health?.disk_usage || 0}%`})}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Uptime</span>
                      <span className="text-sm font-medium">{stats?.system_health?.uptime_hours || 0}h</span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {stats?.system_health?.uptime_percentage || 100}% availability
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Overview;