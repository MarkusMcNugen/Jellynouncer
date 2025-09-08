import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { useEffect, useState, lazy, Suspense } from 'react'
import logger from './services/logger'
import RouteLogger from './components/RouteLogger'
import withLifecycleLogging from './utils/withLifecycleLogging'

// Keep Layout and Login as regular imports (needed immediately)
import Layout from './components/Layout'
import Login from './pages/Login'

// Lazy load all other routes
const Overview = lazy(() => import('./pages/Overview'))
const Config = lazy(() => import('./pages/Config'))
const Templates = lazy(() => import('./pages/Templates'))
const Backups = lazy(() => import('./pages/Backups'))
const Logs = lazy(() => import('./pages/Logs'))
const Notifications = lazy(() => import('./pages/Notifications'))

// Loading component
const PageLoading = () => (
  <div className="flex items-center justify-center min-h-[50vh]">
    <div className="text-gray-500 dark:text-gray-400">Loading...</div>
  </div>
)

// Wrap lazy-loaded components with lifecycle logging
const LoggedOverview = withLifecycleLogging(Overview, 'Overview');
const LoggedConfig = withLifecycleLogging(Config, 'Config');
const LoggedTemplates = withLifecycleLogging(Templates, 'Templates');
const LoggedBackups = withLifecycleLogging(Backups, 'Backups');
const LoggedLogs = withLifecycleLogging(Logs, 'Logs');
const LoggedNotifications = withLifecycleLogging(Notifications, 'Notifications');
const LoggedLayout = withLifecycleLogging(Layout, 'Layout');

function App() {
  const { isAuthenticated, authRequired, checkAuth } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Log app initialization with more details
    logger.info('[App] Jellynouncer Web Interface initializing', {
      version: '1.0.0',
      environment: import.meta.env.MODE,
      url: window.location.href,
      userAgent: navigator.userAgent,
      screen: {
        width: window.screen.width,
        height: window.screen.height
      }
    })
    
    // Check if user is authenticated on app load
    const initAuth = async () => {
      const authTimer = logger.startTimer('[App] Authentication check');
      try {
        logger.debug('[App] Starting authentication status check')
        await checkAuth()
        logger.debug('[App] Authentication check completed', {
          authRequired,
          isAuthenticated,
          authState: authRequired ? (isAuthenticated ? 'authenticated' : 'needs-login') : 'no-auth-required'
        })
        authTimer.end();
      } catch (error) {
        logger.error('[App] Authentication check failed', {
          error: error.message,
          stack: error.stack,
          authRequired,
          isAuthenticated
        })
        authTimer.end();
      } finally {
        logger.debug('[App] Setting loading state to false');
        setLoading(false)
      }
    }
    initAuth()
  }, [checkAuth, authRequired, isAuthenticated])

  // Log successful app load
  useEffect(() => {
    if (!loading) {
      logger.info('[App] Application loaded successfully', {
        authRequired,
        isAuthenticated,
        renderMode: authRequired ? (isAuthenticated ? 'main-app' : 'login') : 'main-app'
      })
    }
  }, [loading, authRequired, isAuthenticated])

  // Log page visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      logger.debug('[App] Page visibility changed', {
        hidden: document.hidden,
        visibilityState: document.visibilityState
      });
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // Log window focus/blur
  useEffect(() => {
    const handleFocus = () => {
      logger.debug('[App] Window gained focus');
    };
    
    const handleBlur = () => {
      logger.debug('[App] Window lost focus');
    };
    
    window.addEventListener('focus', handleFocus);
    window.addEventListener('blur', handleBlur);
    
    return () => {
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('blur', handleBlur);
    };
  }, []);

  // Show loading spinner while checking auth
  if (loading) {
    logger.debug('[App] Rendering loading spinner');
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  // Only show login if auth is required and user is not authenticated
  if (authRequired && !isAuthenticated) {
    logger.debug('[App] Rendering login page - authentication required', {
      authRequired,
      isAuthenticated
    });
    return <Login />
  }

  logger.debug('[App] Rendering main application routes', {
    authRequired,
    isAuthenticated,
    path: window.location.pathname
  });

  return (
    <>
      <RouteLogger />
      <Routes>
        <Route path="/" element={<LoggedLayout />}>
          <Route index element={
            <Suspense fallback={<PageLoading />}>
              <LoggedOverview />
            </Suspense>
          } />
          <Route path="config" element={
            <Suspense fallback={<PageLoading />}>
              <LoggedConfig />
            </Suspense>
          } />
          <Route path="templates" element={
            <Suspense fallback={<PageLoading />}>
              <LoggedTemplates />
            </Suspense>
          } />
          <Route path="backups" element={
            <Suspense fallback={<PageLoading />}>
              <LoggedBackups />
            </Suspense>
          } />
          <Route path="logs" element={
            <Suspense fallback={<PageLoading />}>
              <LoggedLogs />
            </Suspense>
          } />
          <Route path="notifications" element={
            <Suspense fallback={<PageLoading />}>
              <LoggedNotifications />
            </Suspense>
          } />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default App