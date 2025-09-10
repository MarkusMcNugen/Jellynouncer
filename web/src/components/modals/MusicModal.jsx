import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, MusicalNoteIcon, ClockIcon } from '@heroicons/react/24/outline'
import { apiService } from '../../services/api'
import logger from '../../services/logger'

export default function MusicModal({ isOpen, onClose, notification }) {
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
      logger.debug(`Fetching music metadata for item ${notification.item_id}`)
      
      const response = await apiService.get(`/jellyfin/item/${notification.item_id}`)
      setMetadata(response.data)
      logger.debug('Music metadata fetched successfully', response.data)
    } catch (err) {
      logger.error('Failed to fetch music metadata:', err)
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

  const formatRuntime = (ticks) => {
    if (!ticks) return null
    const seconds = Math.round(ticks / 10000000)
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}:${String(secs).padStart(2, '0')}`
  }

  const isAlbum = metadata?.type === 'musicalbum' || notification?.item_type?.toLowerCase() === 'musicalbum'

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
                <div className="relative h-48 bg-gradient-to-br from-green-500 to-teal-600">
                  {metadata?.backdrop_url && !metadata.deleted && (
                    <img 
                      src={metadata.backdrop_url} 
                      alt="" 
                      className="absolute inset-0 w-full h-full object-cover opacity-50"
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
                          className="w-24 h-24 object-cover rounded-lg shadow-lg"
                        />
                      ) : (
                        <div className="w-24 h-24 bg-gray-700 rounded-lg shadow-lg flex items-center justify-center">
                          <MusicalNoteIcon className="h-12 w-12 text-gray-500" />
                        </div>
                      )}
                      <div className="flex-1 text-white">
                        <h2 className="text-2xl font-bold mb-1">{metadata?.name || notification?.item_name}</h2>
                        {(metadata?.artists || metadata?.album_artist) && (
                          <p className="text-lg opacity-90">
                            {metadata.artists?.join(', ') || metadata.album_artist}
                          </p>
                        )}
                        {!isAlbum && metadata?.album && (
                          <p className="text-sm opacity-75 mt-1">from {metadata.album}</p>
                        )}
                        <div className="flex gap-4 mt-2 text-sm">
                          {metadata?.year && (
                            <span>{metadata.year}</span>
                          )}
                          {metadata?.runtime_ticks && (
                            <span className="flex items-center gap-1">
                              <ClockIcon className="h-4 w-4" />
                              {formatRuntime(metadata.runtime_ticks)}
                            </span>
                          )}
                          {isAlbum && metadata?.track_count && (
                            <span>{metadata.track_count} tracks</span>
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
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
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
                      {/* Track/Album Info */}
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          {!isAlbum && (
                            <>
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Track</p>
                                <p className="font-medium text-gray-900 dark:text-white">
                                  {metadata?.track_number ? `#${metadata.track_number}` : '-'}
                                  {metadata?.disc_number > 1 && ` (Disc ${metadata.disc_number})`}
                                </p>
                              </div>
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Album</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata?.album || 'Unknown'}</p>
                              </div>
                            </>
                          )}
                          {isAlbum && (
                            <>
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Album Artist</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata?.album_artist || 'Various Artists'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500 dark:text-gray-400">Tracks</p>
                                <p className="font-medium text-gray-900 dark:text-white">{metadata?.track_count || 0}</p>
                              </div>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Genres */}
                      {metadata?.genres && metadata.genres.length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Genres</h3>
                          <div className="flex flex-wrap gap-2">
                            {metadata.genres.map((genre, idx) => (
                              <span key={idx} className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm">
                                {genre}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Technical Details */}
                      {metadata?.audio_codec && (
                        <div>
                          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Audio Details</h3>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-gray-500 dark:text-gray-400">Codec:</span>
                              <span className="ml-2 text-gray-900 dark:text-white font-medium">{metadata.audio_codec.toUpperCase()}</span>
                            </div>
                            {metadata?.audio_channels && (
                              <div>
                                <span className="text-gray-500 dark:text-gray-400">Channels:</span>
                                <span className="ml-2 text-gray-900 dark:text-white font-medium">{metadata.audio_channels}</span>
                              </div>
                            )}
                            {metadata?.container && (
                              <div>
                                <span className="text-gray-500 dark:text-gray-400">Format:</span>
                                <span className="ml-2 text-gray-900 dark:text-white font-medium">{metadata.container.toUpperCase()}</span>
                              </div>
                            )}
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
                          {notification?.event_type === 'new' ? (isAlbum ? 'New Album Added' : 'New Track Added') :
                           notification?.event_type === 'upgraded' ? 'Quality Upgraded' :
                           notification?.event_type === 'deleted' ? (isAlbum ? 'Album Removed' : 'Track Removed') :
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