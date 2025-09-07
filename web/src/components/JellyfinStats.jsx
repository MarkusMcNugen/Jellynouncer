import React from 'react';
import { Icon, IconDuotone, IconLight } from './FontAwesomeIcon';

const JellyfinStats = ({ stats }) => {
  if (!stats) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Jellyfin Server
        </h2>
        <p className="text-gray-500 dark:text-gray-400">Loading server information...</p>
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
        return 'text-green-500 bg-green-100 dark:bg-green-900';
      case 'error':
        return 'text-red-500 bg-red-100 dark:bg-red-900';
      case 'offline':
        return 'text-gray-500 bg-gray-100 dark:bg-gray-700';
      default:
        return 'text-yellow-500 bg-yellow-100 dark:bg-yellow-900';
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num?.toString() || '0';
  };

  const libraries = stats.library_stats || {};
  const systemInfo = stats.system_info || {};

  return (
    <div className="space-y-6">
      {/* Server Status Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <IconDuotone icon="server" className="mr-2 text-purple-500" />
            Jellyfin Server
          </h2>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(stats.server_status)}`}>
            {stats.server_status || 'Unknown'}
          </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Server Name</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {stats.server_name || 'Unknown'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Version</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {stats.server_version || 'Unknown'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Server ID</p>
            <p className="font-medium text-gray-900 dark:text-white text-xs truncate">
              {stats.server_id || 'Unknown'}
            </p>
          </div>
        </div>

        {stats.last_error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">
              <IconDuotone icon="triangle-exclamation" className="mr-2 text-yellow-500" />
              {stats.last_error}
            </p>
          </div>
        )}
      </div>

      {/* Media Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <IconDuotone icon="film" size="2x" className="text-blue-500" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(stats.movie_count)}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Movies</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <IconDuotone icon="tv" size="2x" className="text-purple-500" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(stats.series_count)}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">TV Shows</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <IconDuotone icon="tv-retro" size="2x" className="text-purple-400" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(stats.episode_count)}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Episodes</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <IconDuotone icon="music" size="2x" className="text-green-500" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(stats.music_count)}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Songs</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <IconDuotone icon="images" size="2x" className="text-yellow-500" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(stats.photo_count)}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Photos</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <IconDuotone icon="book-open" size="2x" className="text-orange-500" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(stats.book_count)}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Books</p>
        </div>
      </div>

      {/* User Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center">
            <IconDuotone icon="users" size="2x" className="text-indigo-500 mr-3" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Users</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.total_users || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center">
            <IconDuotone icon="user-check" size="2x" className="text-green-500 mr-3" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Active Users</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.active_users || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center">
            <IconDuotone icon="database" size="2x" className="text-blue-500 mr-3" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Items</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(stats.total_items)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Libraries */}
      {Object.keys(libraries).length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Libraries
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(libraries).map(([name, lib]) => (
              <div key={lib.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{name}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                      {lib.type || 'mixed'}
                    </p>
                  </div>
                  <span className="text-lg font-semibold text-purple-600 dark:text-purple-400">
                    {formatNumber(lib.item_count)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Information */}
      {systemInfo.operating_system && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <IconDuotone icon="microchip" className="mr-2" />
            System Information
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Operating System</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {systemInfo.operating_system}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Architecture</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {systemInfo.architecture}
              </p>
            </div>
            {systemInfo.has_update && (
              <div className="md:col-span-2">
                <div className="flex items-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <IconDuotone icon="arrow-alt-circle-up" className="text-yellow-600 mr-2" />
                  <span className="text-sm text-yellow-800 dark:text-yellow-200">
                    Update available for Jellyfin server
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Last Updated */}
      {stats.last_check && (
        <div className="text-center text-sm text-gray-500 dark:text-gray-400">
          Last updated: {new Date(stats.last_check).toLocaleString()}
        </div>
      )}
    </div>
  );
};

export default JellyfinStats;