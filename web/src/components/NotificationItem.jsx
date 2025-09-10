import { Icon } from './FontAwesomeIcon';

const NotificationItem = ({ notification, onClick }) => {
  // Helper to format relative time
  const getRelativeTime = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  // Helper to get status color and icon
  const getStatusInfo = (status) => {
    switch (status) {
      case 'sent':
        return {
          color: 'text-green-600 dark:text-green-400',
          bgColor: 'bg-green-50 dark:bg-green-900/20',
          borderColor: 'border-green-200 dark:border-green-800',
          icon: 'check-circle',
          label: 'Sent'
        };
      case 'failed':
        return {
          color: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-50 dark:bg-red-900/20',
          borderColor: 'border-red-200 dark:border-red-800',
          icon: 'times-circle',
          label: 'Failed'
        };
      case 'pending':
        return {
          color: 'text-yellow-600 dark:text-yellow-400',
          bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
          borderColor: 'border-yellow-200 dark:border-yellow-800',
          icon: 'clock',
          label: 'Pending'
        };
      default:
        return {
          color: 'text-gray-600 dark:text-gray-400',
          bgColor: 'bg-gray-50 dark:bg-gray-900/20',
          borderColor: 'border-gray-200 dark:border-gray-800',
          icon: 'question-circle',
          label: 'Unknown'
        };
    }
  };

  // Helper to get event info
  const getEventInfo = (event) => {
    switch (event) {
      case 'new':
        return {
          icon: 'plus-circle',
          color: 'text-blue-600 dark:text-blue-400',
          label: 'New'
        };
      case 'upgraded':
        return {
          icon: 'arrow-up-circle',
          color: 'text-purple-600 dark:text-purple-400',
          label: 'Upgraded'
        };
      case 'deleted':
        return {
          icon: 'trash',
          color: 'text-red-600 dark:text-red-400',
          label: 'Deleted'
        };
      default:
        return {
          icon: 'circle-info',
          color: 'text-gray-600 dark:text-gray-400',
          label: event
        };
    }
  };

  // Helper to get media type icon and color
  const getTypeInfo = (type) => {
    const typeStr = type?.toLowerCase() || '';
    if (typeStr.includes('movie')) {
      return { icon: 'film', color: 'text-purple-600 dark:text-purple-400' };
    }
    if (typeStr.includes('episode')) {
      return { icon: 'tv', color: 'text-blue-600 dark:text-blue-400' };
    }
    if (typeStr.includes('series') || typeStr.includes('show')) {
      return { icon: 'tv', color: 'text-cyan-600 dark:text-cyan-400' };
    }
    if (typeStr.includes('season')) {
      return { icon: 'list', color: 'text-indigo-600 dark:text-indigo-400' };
    }
    if (typeStr.includes('music') || typeStr.includes('audio')) {
      return { icon: 'music', color: 'text-green-600 dark:text-green-400' };
    }
    if (typeStr.includes('book')) {
      return { icon: 'book', color: 'text-orange-600 dark:text-orange-400' };
    }
    if (typeStr.includes('photo')) {
      return { icon: 'image', color: 'text-pink-600 dark:text-pink-400' };
    }
    return { icon: 'folder', color: 'text-gray-600 dark:text-gray-400' };
  };

  const statusInfo = getStatusInfo(notification.status);
  const eventInfo = getEventInfo(notification.event);
  const typeInfo = getTypeInfo(notification.type);

  // Parse metadata for additional info
  let metadata = notification.metadata;
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata);
    } catch {
      metadata = null;
    }
  }

  return (
    <div
      onClick={onClick}
      className={`
        border rounded-lg p-4 cursor-pointer transition-all duration-200
        hover:shadow-md hover:scale-[1.01]
        ${statusInfo.bgColor} ${statusInfo.borderColor}
      `}
    >
      <div className="flex items-start justify-between">
        {/* Left side - Main content */}
        <div className="flex-1 min-w-0">
          {/* Title row with icons */}
          <div className="flex items-center gap-2 mb-2">
            <Icon icon={typeInfo.icon} className={typeInfo.color} size="lg" />
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white truncate flex-1">
              {notification.name}
            </h4>
          </div>

          {/* Info badges */}
          <div className="flex flex-wrap items-center gap-2 mb-2">
            {/* Event type badge */}
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-white dark:bg-gray-800">
              <Icon icon={eventInfo.icon} className={`${eventInfo.color} mr-1`} size="xs" />
              {eventInfo.label}
            </span>

            {/* Media type badge */}
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300">
              {notification.type}
            </span>

            {/* Additional metadata badges */}
            {metadata?.changes && Array.isArray(metadata.changes) && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300">
                {metadata.changes.length} changes
              </span>
            )}
          </div>

          {/* Error message if failed */}
          {notification.status === 'failed' && notification.error_message && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1 line-clamp-2">
              {notification.error_message}
            </p>
          )}
        </div>

        {/* Right side - Status and time */}
        <div className="flex flex-col items-end ml-4">
          {/* Status indicator */}
          <div className={`flex items-center ${statusInfo.color} mb-1`}>
            <Icon icon={statusInfo.icon} className="mr-1" size="sm" />
            <span className="text-xs font-medium">{statusInfo.label}</span>
          </div>

          {/* Timestamp */}
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {getRelativeTime(notification.timestamp)}
          </span>

          {/* Processing time if available */}
          {notification.processing_time_ms && (
            <span className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {notification.processing_time_ms}ms
            </span>
          )}
        </div>
      </div>

      {/* Click hint */}
      <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
          <Icon icon="mouse-pointer" className="mr-1" size="xs" />
          Click for details
        </p>
      </div>
    </div>
  );
};

export default NotificationItem;