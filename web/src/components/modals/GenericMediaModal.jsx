import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, TvIcon, FolderIcon, PhotoIcon, BookOpenIcon } from '@heroicons/react/24/outline'
import { apiService } from '../../services/api'
import logger from '../../services/logger'

const getIcon = (type) => {
  switch(type?.toLowerCase()) {
    case 'series': return TvIcon
    case 'season': return FolderIcon
    case 'photo': return PhotoIcon
    case 'book': return BookOpenIcon
    default: return FolderIcon
  }
}

export default function GenericMediaModal({ isOpen, onClose, notification }) {
  const [metadata, setMetadata] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen && notification?.item_id && notification.event_type !== 'deleted') {
      fetchMetadata()
    } else if (notification?.event_type === 'deleted') {
      setMetadata({
        name: notification.item_name,
        type: notification.item_type?.toLowerCase(),
        deleted: true
      })
    }
  }, [isOpen, notification])

  const fetchMetadata = async () => {
    try {
      setLoading(true)
      setError(null)
      logger.debug(`Fetching metadata for ${notification.item_type} ${notification.item_id}`)
      
      const response = await apiService.get(`/jellyfin/item/${notification.item_id}`)
      setMetadata(response.data)
      logger.debug('Metadata fetched successfully', response.data)
    } catch (err) {
      logger.error('Failed to fetch metadata:', err)
      setError(err.message)
      setMetadata({
        name: notification.item_name,
        type: notification.item_type?.toLowerCase(),
        error: true
      })
    } finally {
      setLoading(false)
    }
  }

  const Icon = getIcon(metadata?.type || notification?.item_type)
  const itemType = metadata?.type || notification?.item_type?.toLowerCase()

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
          <div className="fixed inset-0 bg-black bg-opacity-75" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 shadow-xl transition-all">
                {/* Header */}
                <div className="relative h-48 bg-gradient-to-br from-indigo-500 to-purple-600">
                  {metadata?.backdrop_url && !metadata.deleted && (
                    <img 
                      src={metadata.backdrop_url} 
                      alt="" 
                      className="absolute inset-0 w-full h-full object-cover opacity-60"
                    />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                  
                  {/* Close button */}
                  <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>

                  {/* Title overlay */}
                  <div className="absolute bottom-0 left-0 right-0 p-6">
                    <div className="flex items-start gap-4">
                      {metadata?.thumbnail_url && !metadata.deleted ? (
                        <img 
                          src={metadata.thumbnail_url} 
                          alt={metadata.name}
                          className="w-24 h-36 object-cover rounded-lg shadow-lg"
                        />
                      ) : (
                        <div className="w-24 h-36 bg-gray-700 rounded-lg shadow-lg flex items-center justify-center">
                          <Icon className="h-12 w-12 text-gray-500" />
                        </div>
                      )}
                      <div className="flex-1 text-white">
                        <div className="text-sm opacity-90 mb-1 capitalize">{itemType}</div>
                        <h2 className="text-2xl font-bold mb-2">{metadata?.name || notification?.item_name}</h2>
                        {itemType === 'series' && metadata?.status && (
                          <span className="inline-block px-2 py-1 bg-white/20 rounded text-sm">
                            {metadata.status}
                          </span>
                        )}
                        {itemType === 'season' && metadata?.series_name && (
                          <p className="text-sm opacity-90">
                            {metadata.series_name} - Season {metadata.season_number}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  {loading ? (
                    <div className="text-center py-8">
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                      <p className="mt-2 text-gray-500 dark:text-gray-400">Loading metadata...</p>
                    </div>
                  ) : error ? (
                    <div className="text-center py-8">
                      <p className="text-red-500">Failed to load additional metadata</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{error}</p>
                    </div>
                  ) : metadata?.deleted ? (
                    <div className="text-center py-8">
                      <p className="text-gray-500 dark:text-gray-400">This item has been deleted from Jellyfin</p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Type-specific info */}
                      {itemType === 'series' && (
                        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            {metadata?.season_count !== undefined && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Seasons</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.season_count}</p>
                              </div>
                            )}
                            {metadata?.episode_count !== undefined && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Episodes</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.episode_count}</p>
                              </div>
                            )}
                            {metadata?.year && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Year</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.year}</p>
                              </div>
                            )}
                            {metadata?.air_time && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Air Time</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.air_time}</p>
                              </div>
                            )}
                            {metadata?.air_days && metadata.air_days.length > 0 && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Airs On</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.air_days.join(', ')}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {itemType === 'season' && (
                        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="text-gray-500 dark:text-gray-400">Series</p>
                              <p className="font-medium text-gray-900 dark:text-white">{metadata?.series_name || 'Unknown'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500 dark:text-gray-400">Season</p>
                              <p className="font-medium text-gray-900 dark:text-white">{metadata?.season_number || '-'}</p>
                            </div>
                            {metadata?.episode_count !== undefined && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Episodes</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.episode_count}</p>
                              </div>
                            )}
                            {metadata?.year && (
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Year</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata.year}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Overview */}
                      {metadata?.overview && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Overview</h3>
                          <p className="text-gray-600 dark:text-gray-300 leading-relaxed">{metadata.overview}</p>
                        </div>
                      )}

                      {/* Genres */}
                      {metadata?.genres && metadata.genres.length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Genres</h3>
                          <div className="flex flex-wrap gap-2">
                            {metadata.genres.map((genre, idx) => (
                              <span key={idx} className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 rounded-full text-sm">
                                {genre}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Studios */}
                      {metadata?.studios && metadata.studios.length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Studios</h3>
                          <div className="flex flex-wrap gap-2">
                            {metadata.studios.map((studio, idx) => (
                              <span key={idx} className="text-sm text-gray-600 dark:text-gray-400">
                                {studio}
                                {idx < metadata.studios.length - 1 && ', '}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Notification Info */}
                  <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between text-sm">
                      <div className="text-gray-500 dark:text-gray-400">
                        <span>Event: </span>
                        <span className={`font-medium ${
                          notification?.event_type === 'new' ? 'text-green-600 dark:text-green-400' :
                          notification?.event_type === 'upgraded' ? 'text-blue-600 dark:text-blue-400' :
                          notification?.event_type === 'deleted' ? 'text-red-600 dark:text-red-400' :
                          'text-gray-600 dark:text-gray-400'
                        }`}>
                          {notification?.event_type === 'new' ? 'Added to Library' :
                           notification?.event_type === 'upgraded' ? 'Quality Upgraded' :
                           notification?.event_type === 'deleted' ? 'Removed from Library' :
                           notification?.event_type}
                        </span>
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">
                        {new Date(notification?.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}