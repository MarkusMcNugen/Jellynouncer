import { lazy, Suspense } from 'react';

// Lazy load type-specific modals for better performance
const MovieModal = lazy(() => import('./modals/MovieModal'));
const EpisodeModal = lazy(() => import('./modals/EpisodeModal'));
const SeriesModal = lazy(() => import('./modals/SeriesModal'));
const SeasonModal = lazy(() => import('./modals/SeasonModal'));
const MusicModal = lazy(() => import('./modals/MusicModal'));
const GenericMediaModal = lazy(() => import('./modals/GenericMediaModal'));

const NotificationModal = ({ notification, isOpen, onClose }) => {
  if (!notification) return null;

  // Determine which modal to use based on item type
  const getModalComponent = () => {
    const itemType = notification.item_type?.toLowerCase() || notification.type?.toLowerCase() || '';
    
    // Route to appropriate modal based on type
    if (itemType.includes('movie')) {
      return <MovieModal isOpen={isOpen} onClose={onClose} notification={notification} />;
    } else if (itemType.includes('episode')) {
      return <EpisodeModal isOpen={isOpen} onClose={onClose} notification={notification} />;
    } else if (itemType.includes('series')) {
      return <SeriesModal isOpen={isOpen} onClose={onClose} notification={notification} />;
    } else if (itemType.includes('season')) {
      return <SeasonModal isOpen={isOpen} onClose={onClose} notification={notification} />;
    } else if (itemType.includes('audio') || itemType.includes('musicalbum')) {
      return <MusicModal isOpen={isOpen} onClose={onClose} notification={notification} />;
    } else {
      // Use generic modal for other types (books, photos, etc.)
      return <GenericMediaModal isOpen={isOpen} onClose={onClose} notification={notification} />;
    }
  };

  // Provide a loading fallback for lazy loaded components
  return (
    <Suspense fallback={
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    }>
      {getModalComponent()}
    </Suspense>
  );
};

export default NotificationModal;