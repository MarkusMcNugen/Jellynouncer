import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, FilmIcon, StarIcon, ClockIcon, CalendarIcon, TagIcon } from '@heroicons/react/24/outline'
import { apiService } from '../../services/api'
import logger from '../../services/logger'

export default function MovieModal({ isOpen, onClose, notification }) {
  const [metadata, setMetadata] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen && notification?.item_id && notification.event_type !== 'deleted') {
      fetchMetadata()
    } else if (notification?.event_type === 'deleted') {
      // For deleted items, use only the notification data
      setMetadata({
        name: notification.item_name,
        type: 'movie',
        deleted: true
      })
    }
  }, [isOpen, notification])

  const fetchMetadata = async () => {
    try {
      setLoading(true)
      setError(null)
      logger.debug(`Fetching movie metadata for item ${notification.item_id}`)
      
      const response = await apiService.get(`/jellyfin/item/${notification.item_id}`)
      setMetadata(response.data)
      logger.debug('Movie metadata fetched successfully', response.data)
    } catch (err) {
      logger.error('Failed to fetch movie metadata:', err)
      setError(err.message)
      // Fall back to notification data
      setMetadata({
        name: notification.item_name,
        type: 'movie',
        error: true
      })
    } finally {
      setLoading(false)
    }
  }

  const formatRuntime = (ticks) => {
    if (!ticks) return null
    const minutes = Math.round(ticks / 600000000)
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return null
    return new Date(dateStr).toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
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
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 shadow-xl transition-all">
                {/* Header with backdrop image */}
                <div className="relative h-64 bg-gradient-to-br from-blue-500 to-purple-600">
                  {metadata?.backdrop_url && !metadata.deleted && (
                    <img 
                      src={metadata.backdrop_url} 
                      alt="" 
                      className="absolute inset-0 w-full h-full object-cover opacity-70"
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
                          className="w-32 h-48 object-cover rounded-lg shadow-lg"
                        />
                      ) : (
                        <div className="w-32 h-48 bg-gray-700 rounded-lg shadow-lg flex items-center justify-center">
                          <FilmIcon className="h-12 w-12 text-gray-500" />
                        </div>
                      )}
                      <div className="flex-1 text-white">
                        <h2 className="text-3xl font-bold mb-2">{metadata?.name || notification?.item_name}</h2>
                        {metadata?.tagline && (
                          <p className="text-sm italic opacity-90 mb-2">"{metadata.tagline}"</p>
                        )}
                        <div className="flex flex-wrap gap-4 text-sm">
                          {metadata?.year && (
                            <span className="flex items-center gap-1">
                              <CalendarIcon className="h-4 w-4" />
                              {metadata.year}
                            </span>
                          )}
                          {metadata?.runtime_ticks && (
                            <span className="flex items-center gap-1">
                              <ClockIcon className="h-4 w-4" />
                              {formatRuntime(metadata.runtime_ticks)}
                            </span>
                          )}
                          {metadata?.community_rating && (
                            <span className="flex items-center gap-1">
                              <StarIcon className="h-4 w-4" />
                              {metadata.community_rating.toFixed(1)}/10
                            </span>
                          )}
                          {metadata?.official_rating && (
                            <span className="px-2 py-0.5 bg-white/20 rounded">
                              {metadata.official_rating}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  {loading ? (
                    <div className="text-center py-8">
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
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
                              <span key={idx} className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm">
                                {genre}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Cast & Crew */}
                      {metadata?.people && metadata.people.length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Cast & Crew</h3>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {metadata.people.map((person, idx) => (
                              <div key={idx} className="flex items-center gap-2">
                                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                                  <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
                                    {person.Name?.charAt(0) || '?'}
                                  </span>
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{person.Name}</p>
                                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{person.Role || person.Type}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Technical Details */}
                      <div>
                        <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Technical Details</h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          {metadata?.resolution && (
                            <div>
                              <span className="text-gray-500 dark:text-gray-400">Resolution:</span>
                              <span className="ml-2 text-gray-900 dark:text-white font-medium">{metadata.resolution}</span>
                              {metadata.hdr && <span className="ml-1 text-yellow-500">HDR</span>}
                            </div>
                          )}
                          {metadata?.video_codec && (
                            <div>
                              <span className="text-gray-500 dark:text-gray-400">Video Codec:</span>
                              <span className="ml-2 text-gray-900 dark:text-white font-medium">{metadata.video_codec.toUpperCase()}</span>
                            </div>
                          )}
                          {metadata?.audio_codec && (
                            <div>
                              <span className="text-gray-500 dark:text-gray-400">Audio:</span>
                              <span className="ml-2 text-gray-900 dark:text-white font-medium">
                                {metadata.audio_codec.toUpperCase()}
                                {metadata.audio_channels && ` ${metadata.audio_channels}ch`}
                              </span>
                            </div>
                          )}
                          {metadata?.container && (
                            <div>
                              <span className="text-gray-500 dark:text-gray-400">Container:</span>
                              <span className="ml-2 text-gray-900 dark:text-white font-medium">{metadata.container.toUpperCase()}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Provider IDs */}
                      {metadata?.provider_ids && Object.keys(metadata.provider_ids).length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">External IDs</h3>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(metadata.provider_ids).map(([provider, id]) => (
                              <span key={provider} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                                <span className="text-gray-500 dark:text-gray-400">{provider}:</span>
                                <span className="ml-1 text-gray-900 dark:text-white font-medium">{id}</span>
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