import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Config from './pages/Config'
import Templates from './pages/Templates'
import Backups from './pages/Backups'
import Logs from './pages/Logs'
import Notifications from './pages/Notifications'
import { useEffect, useState } from 'react'
import logger from './services/logger'
import RouteLogger from './components/RouteLogger'
import withLifecycleLogging from './utils/withLifecycleLogging'

// Wrap page components with lifecycle logging
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
  }, [checkAuth])

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
          <Route index element={<LoggedOverview />} />
          <Route path="config" element={<LoggedConfig />} />
          <Route path="templates" element={<LoggedTemplates />} />
          <Route path="backups" element={<LoggedBackups />} />
          <Route path="logs" element={<LoggedLogs />} />
          <Route path="notifications" element={<LoggedNotifications />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default App