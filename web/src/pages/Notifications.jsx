import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { IconSolid } from '../components/FontAwesomeIcon';
import NotificationModal from '../components/NotificationModal';
import logger from '../services/logger';

const Notifications = () => {
  logger.info('[Notifications] Component initialization started');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  
  const itemsPerPage = 50;
  
  const fetchNotifications = async (page = 1) => {
    logger.debug('[Notifications] Fetching notifications', { page, itemsPerPage });
    
    try {
      setRefreshing(true);
      
      // API call with pagination parameters
      const response = await apiService.getNotifications({
        page,
        limit: itemsPerPage,
        hours: 24  // Last 24 hours
      });
      
      logger.info('[Notifications] Data received', {
        count: response.data?.notifications?.length || 0,
        total: response.data?.total || 0,
        page: response.data?.page || 1
      });
      
      setNotifications(response.data?.notifications || []);
      setTotalCount(response.data?.total || 0);
      setTotalPages(Math.ceil((response.data?.total || 0) / itemsPerPage));
      setCurrentPage(page);
      setError(null);
      
    } catch (err) {
      logger.error('[Notifications] Error fetching data', {
        message: err.message,
        status: err.response?.status
      });
      setError('Failed to fetch notifications');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  
  useEffect(() => {
    logger.debug('[Notifications] useEffect triggered - initial mount');
    void fetchNotifications(1);
  }, []);
  
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      logger.debug('[Notifications] Page change requested', { from: currentPage, to: newPage });
      fetchNotifications(newPage);
    }
  };
  
  const getContentIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'movie':
        return 'film';
      case 'series':
        return 'tv-retro';
      case 'episode':
        return 'video';
      case 'music':
      case 'audio':
        return 'music';
      default:
        return 'folder';
    }
  };
  
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 4) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    return date.toLocaleString();
  };
  
  if (loading && !notifications.length) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }
  
  return (
    <div className="-mx-4 sm:-mx-6 lg:-mx-8">
      <div className="px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Header with Back Button */}
        <div className="flex items-center justify-between pt-4">
          <div className="flex items-center gap-4">
            <Link 
              to="/overview"
              className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <IconSolid icon="arrow-left" className="mr-2" />
              Back to Overview
            </Link>
            
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">All Notifications</h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Showing notifications from the last 24 hours ({totalCount} total)
              </p>
            </div>
          </div>
          
          <button
            onClick={() => fetchNotifications(currentPage)}
            disabled={refreshing}
            className={`
              inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md
              text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 
              focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed
            `}
          >
            <IconSolid icon="arrows-rotate" className={`mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
        
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}
        
        {/* Notifications List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-6">
            {notifications.length > 0 ? (
              <div className="space-y-4">
                {notifications.map((notification, index) => (
                  <div 
                    key={`${notification.id}-${index}`} 
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                    onClick={() => {
                      logger.debug('[Notifications] Opening modal for notification', notification);
                      setSelectedNotification(notification);
                      setModalOpen(true);
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        {/* Header row with icon, title, and badges */}
                        <div className="flex items-start gap-3 mb-2">
                          <div className="flex-shrink-0 mt-1">
                            <IconSolid icon={getContentIcon(notification.type)} className="text-purple-600 dark:text-purple-400" size="lg" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap mb-2">
                              <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {notification.name || 'Unknown Item'}
                              </h4>
                              <span className={`
                                inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                ${notification.event === 'new' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                                  notification.event === 'upgraded' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                                  notification.event === 'deleted' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                  'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}
                              `}>
                                {notification.event || 'unknown'}
                              </span>
                              <span className={`
                                inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                ${notification.status === 'sent' || notification.status === 'success' ? 
                                  'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                                  notification.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                  'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}
                              `}>
                                <IconSolid icon={notification.status === 'sent' || notification.status === 'success' ? 'circle-check' : 
                                            notification.status === 'failed' ? 'circle-xmark' : 'clock'} 
                                      className="mr-1" size="xs" />
                                {notification.status || 'pending'}
                              </span>
                            </div>
                            
                            {/* Details Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-2 text-sm">
                              <div className="flex items-center text-gray-600 dark:text-gray-400">
                                <IconSolid icon="clock" className="mr-2" size="sm" />
                                <span title={new Date(notification.timestamp).toLocaleString()}>
                                  {formatTimestamp(notification.timestamp)}
                                </span>
                              </div>
                              
                              {notification.type && (
                                <div className="flex items-center text-gray-600 dark:text-gray-400">
                                  <IconSolid icon="tag" className="mr-2" size="sm" />
                                  <span className="capitalize">{notification.type}</span>
                                </div>
                              )}
                              
                              {/* Discord Channel */}
                              {notification.discord_webhook && (
                                <div className="flex items-center text-gray-600 dark:text-gray-400">
                                  <IconSolid icon="message-dots" className="mr-2" size="sm" />
                                  <span className="font-medium">
                                    {notification.discord_webhook.includes('movies') ? '🎬 Movies' :
                                     notification.discord_webhook.includes('tv') ? '📺 TV Shows' :
                                     notification.discord_webhook.includes('music') ? '🎵 Music' :
                                     '📢 Default'} Channel
                                  </span>
                                </div>
                              )}
                              
                              {/* Processing Time */}
                              {notification.processing_time_ms && (
                                <div className="flex items-center text-gray-600 dark:text-gray-400">
                                  <IconSolid icon="bolt" className="mr-2" size="sm" />
                                  <span className={notification.processing_time_ms > 1000 ? 'text-yellow-600 dark:text-yellow-400 font-medium' : ''}>
                                    {notification.processing_time_ms}ms
                                  </span>
                                </div>
                              )}
                              
                              {/* Item ID for debugging */}
                              {notification.id && (
                                <div className="flex items-center text-gray-500 dark:text-gray-500 text-xs">
                                  <IconSolid icon="fingerprint" className="mr-2" size="sm" />
                                  <span className="font-mono">{notification.id}</span>
                                </div>
                              )}
                            </div>
                            
                            {/* Error Message */}
                            {notification.status === 'failed' && notification.error_message && (
                              <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                                <div className="flex items-start">
                                  <IconSolid icon="circle-exclamation" className="text-red-500 mr-2 mt-0.5 flex-shrink-0" size="sm" />
                                  <div className="text-sm text-red-700 dark:text-red-300">
                                    <span className="font-medium">Error: </span>
                                    {notification.error_message}
                                  </div>
                                </div>
                              </div>
                            )}
                            
                            {/* Upgrade Changes */}
                            {notification.event === 'upgraded' && notification.metadata?.changes && (
                              <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
                                <div className="flex items-start">
                                  <IconSolid icon="arrow-trend-up" className="text-blue-500 mr-2 mt-0.5 flex-shrink-0" size="sm" />
                                  <div className="text-sm text-blue-700 dark:text-blue-300">
                                    <span className="font-medium">Quality Improvements:</span>
                                    <ul className="mt-1 space-y-0.5">
                                      {Object.entries(notification.metadata.changes).map(([key, value]) => (
                                        <li key={key} className="flex items-center">
                                          <span className="text-blue-600 dark:text-blue-400 mr-2">•</span>
                                          <span className="capitalize">
                                            {key.replace(/_/g, ' ')}: <span className="font-medium">{value}</span>
                                          </span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <IconSolid icon="bell-slash" className="mx-auto text-gray-400 dark:text-gray-600 mb-4" size="3x" />
                <p className="text-gray-500 dark:text-gray-400">No notifications found</p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                  There are no notifications from the last 24 hours
                </p>
              </div>
            )}
          </div>
          
          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-700 dark:text-gray-300">
                  Showing <span className="font-medium">{((currentPage - 1) * itemsPerPage) + 1}</span> to{' '}
                  <span className="font-medium">{Math.min(currentPage * itemsPerPage, totalCount)}</span> of{' '}
                  <span className="font-medium">{totalCount}</span> notifications
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <IconSolid icon="chevron-left" className="mr-1" size="sm" />
                    Previous
                  </button>
                  
                  <div className="flex items-center gap-1">
                    {/* Page numbers */}
                    {[...Array(Math.min(5, totalPages))].map((_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className={`
                            relative inline-flex items-center px-4 py-2 text-sm font-medium rounded-md
                            ${pageNum === currentPage
                              ? 'z-10 bg-purple-600 text-white'
                              : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                            }
                          `}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  
                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <IconSolid icon="chevron-right" className="ml-1" size="sm" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Notification Detail Modal */}
      <NotificationModal
        notification={selectedNotification}
        isOpen={modalOpen}
        onClose={() => {
          logger.debug('[Notifications] Closing modal');
          setModalOpen(false);
          setSelectedNotification(null);
        }}
      />
    </div>
  );
};

export default Notifications;