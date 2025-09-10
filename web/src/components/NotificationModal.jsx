import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Icon } from './FontAwesomeIcon';

const NotificationModal = ({ notification, isOpen, onClose }) => {
  if (!notification) return null;

  // Helper to format timestamp
  const formatTime = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  // Helper to get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'sent':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
      case 'failed':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  // Helper to get event icon
  const getEventIcon = (event) => {
    switch (event) {
      case 'new':
        return 'plus-circle';
      case 'upgraded':
        return 'arrow-up-circle';
      case 'deleted':
        return 'trash';
      default:
        return 'circle-info';
    }
  };

  // Helper to get media type icon
  const getTypeIcon = (type) => {
    const typeStr = type?.toLowerCase() || '';
    if (typeStr.includes('movie')) return 'film';
    if (typeStr.includes('episode')) return 'tv';
    if (typeStr.includes('series') || typeStr.includes('show')) return 'tv';
    if (typeStr.includes('season')) return 'list';
    if (typeStr.includes('music') || typeStr.includes('audio')) return 'music';
    if (typeStr.includes('book')) return 'book';
    if (typeStr.includes('photo')) return 'image';
    return 'folder';
  };

  // Parse metadata if it's a string
  let metadata = notification.metadata;
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata);
    } catch {
      metadata = null;
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 p-6 text-left align-middle shadow-xl transition-all">
                <Dialog.Title
                  as="h3"
                  className="text-lg font-medium leading-6 text-gray-900 dark:text-white flex items-center justify-between"
                >
                  <div className="flex items-center">
                    <Icon icon={getEventIcon(notification.event)} className="mr-2" size="lg" />
                    Notification Details
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  >
                    <Icon icon="times" />
                  </button>
                </Dialog.Title>

                <div className="mt-4 space-y-4">
                  {/* Header with status */}
                  <div className="flex items-center justify-between">
                    <h4 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
                      <Icon icon={getTypeIcon(notification.type)} className="mr-2" />
                      {notification.name}
                    </h4>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(notification.status)}`}>
                      {notification.status}
                    </span>
                  </div>

                  {/* Basic Information */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Type</p>
                      <p className="font-medium text-gray-900 dark:text-white">{notification.type || 'Unknown'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Event</p>
                      <p className="font-medium text-gray-900 dark:text-white capitalize">{notification.event}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Item ID</p>
                      <p className="font-mono text-sm text-gray-900 dark:text-white">{notification.id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Timestamp</p>
                      <p className="text-sm text-gray-900 dark:text-white">{formatTime(notification.timestamp)}</p>
                    </div>
                  </div>

                  {/* Processing Info */}
                  {notification.processing_time_ms && (
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Processing Time</p>
                      <p className="font-medium text-gray-900 dark:text-white">{notification.processing_time_ms}ms</p>
                    </div>
                  )}

                  {/* Discord Webhook */}
                  {notification.discord_webhook && (
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Discord Webhook</p>
                      <p className="font-mono text-xs text-gray-900 dark:text-white truncate">
                        {notification.discord_webhook}
                      </p>
                    </div>
                  )}

                  {/* Error Message */}
                  {notification.error_message && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                      <p className="text-sm font-medium text-red-800 dark:text-red-300 mb-1">Error Message</p>
                      <p className="text-sm text-red-700 dark:text-red-400">{notification.error_message}</p>
                    </div>
                  )}

                  {/* Metadata */}
                  {metadata && (
                    <div>
                      <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Additional Metadata</p>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        {/* Changes for upgraded items */}
                        {metadata.changes && Array.isArray(metadata.changes) && (
                          <div className="space-y-2">
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Changes Detected:</p>
                            {metadata.changes.map((change, idx) => (
                              <div key={idx} className="flex items-center text-sm">
                                <Icon icon="arrow-right" className="mr-2 text-blue-500" size="sm" />
                                <span className="text-gray-600 dark:text-gray-400">{change}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Other metadata fields */}
                        {Object.entries(metadata).map(([key, value]) => {
                          if (key === 'changes') return null; // Already handled above
                          if (typeof value === 'object') {
                            return (
                              <div key={key} className="mt-2">
                                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                                  {key.replace(/_/g, ' ')}:
                                </p>
                                <pre className="text-xs text-gray-600 dark:text-gray-400 mt-1 overflow-x-auto">
                                  {JSON.stringify(value, null, 2)}
                                </pre>
                              </div>
                            );
                          }
                          return (
                            <div key={key} className="flex justify-between py-1">
                              <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                                {key.replace(/_/g, ' ')}:
                              </span>
                              <span className="text-sm font-medium text-gray-900 dark:text-white">
                                {value}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Raw JSON (collapsible) */}
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                      View Raw Data
                    </summary>
                    <pre className="mt-2 text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded-lg overflow-x-auto">
                      {JSON.stringify(notification, null, 2)}
                    </pre>
                  </details>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    type="button"
                    className="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:bg-blue-900 dark:text-blue-100 dark:hover:bg-blue-800"
                    onClick={onClose}
                  >
                    Close
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};

export default NotificationModal;