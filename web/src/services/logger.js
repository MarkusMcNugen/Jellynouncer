/**
 * Client-Side Logging Service for Jellynouncer Web Interface
 * 
 * This module provides comprehensive logging for the React frontend with:
 * - Multiple log levels (debug, info, warn, error)
 * - Session tracking with unique IDs
 * - Batched log sending to reduce server load
 * - Local storage fallback for offline scenarios
 * - Automatic environment detection
 * - Performance monitoring
 * 
 * All logs are sent to the backend API which writes them to jellynouncer.log
 * alongside server logs for unified debugging.
 */

import log from 'loglevel';

// Configuration
const LOG_BATCH_SIZE = 20; // Number of logs to batch before sending
const LOG_BATCH_INTERVAL = 5000; // Send logs every 5 seconds
const MAX_STORED_LOGS = 100; // Maximum logs to store in localStorage
const LOG_STORAGE_KEY = 'jellynouncer_pending_logs';
const SESSION_ID_KEY = 'jellynouncer_session_id';

class ClientLogger {
  constructor() {
    this.logQueue = [];
    this.sessionId = this.getOrCreateSessionId();
    this.isOnline = navigator.onLine;
    this.batchTimer = null;
    this.isSending = false;
    this.configLogLevel = null;
    
    // Configure loglevel based on environment
    // Default to 'info', will be updated from backend config
    const isDev = import.meta.env.DEV;
    const urlParams = new URLSearchParams(window.location.search);
    const debugParam = urlParams.get('debug');
    
    // Check for debug mode from various sources
    if (debugParam === 'true' || localStorage.getItem('debug_mode') === 'true') {
      log.setLevel('debug');
      console.log('[Logger] Debug mode enabled via URL parameter or localStorage');
    } else {
      log.setLevel('info'); // Default to info, will update from config
    }
    
    // Fetch actual log level from backend configuration
    this.fetchLogLevel()
    
    // Store original methods
    this.originalMethods = {
      debug: log.debug.bind(log),
      info: log.info.bind(log),
      warn: log.warn.bind(log),
      error: log.error.bind(log)
    };
    
    // Override loglevel methods to intercept logs
    this.setupInterceptors();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Load any pending logs from localStorage
    this.loadPendingLogs();
    
    // Start batch timer
    this.startBatchTimer();
    
    // Log initialization
    this.info('Client logger initialized', {
      sessionId: this.sessionId,
      logLevel: log.getLevel(),
      environment: import.meta.env.MODE,
      userAgent: navigator.userAgent,
      screen: {
        width: window.screen.width,
        height: window.screen.height,
        pixelRatio: window.devicePixelRatio
      }
    });
  }
  
  async fetchLogLevel() {
    try {
      // Try to get log level from backend config
      const response = await fetch('/api/config');
      if (response.ok) {
        const config = await response.json();
        const backendLogLevel = config?.server?.log_level?.toLowerCase();
        
        if (backendLogLevel && this.configLogLevel !== backendLogLevel) {
          this.configLogLevel = backendLogLevel;
          
          // Map backend log levels to loglevel library levels
          const levelMap = {
            'debug': 'debug',
            'info': 'info',
            'warning': 'warn',
            'warn': 'warn',
            'error': 'error'
          };
          
          const mappedLevel = levelMap[backendLogLevel] || 'info';
          
          // Only update if not in debug mode from URL/localStorage
          const urlParams = new URLSearchParams(window.location.search);
          const debugParam = urlParams.get('debug');
          if (debugParam !== 'true' && localStorage.getItem('debug_mode') !== 'true') {
            log.setLevel(mappedLevel);
            this.originalMethods.info(`[Logger] Log level updated from backend config: ${mappedLevel}`);
          }
        }
      }
    } catch (error) {
      // Silently fail, use default log level
      this.originalMethods.debug('[Logger] Could not fetch backend log level:', error);
    }
  }
  
  getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem(SESSION_ID_KEY);
    if (!sessionId) {
      // Generate unique session ID
      sessionId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem(SESSION_ID_KEY, sessionId);
    }
    return sessionId;
  }
  
  setupInterceptors() {
    // Intercept all log methods
    ['debug', 'info', 'warn', 'error'].forEach(level => {
      log[level] = (...args) => {
        // Call original method for console output
        this.originalMethods[level](...args);
        
        // Add to queue for server sending
        this.addToQueue(level, args);
      };
    });
  }
  
  setupEventListeners() {
    // Monitor online/offline status
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.originalMethods.info('Connection restored');
      this.flushLogs(); // Send any pending logs
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.originalMethods.warn('Connection lost - logs will be queued');
    });
    
    // Send logs before page unload
    window.addEventListener('beforeunload', () => {
      this.flushLogs(true); // Force synchronous send
    });
    
    // Monitor page visibility
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.originalMethods.debug('Page hidden - flushing logs');
        this.flushLogs();
      } else {
        this.originalMethods.debug('Page visible');
      }
    });
    
    // Global error handler
    window.addEventListener('error', (event) => {
      this.error('Uncaught error', {
        message: event.message,
        filename: event.filename,
        line: event.lineno,
        column: event.colno,
        stack: event.error?.stack
      });
    });
    
    // Promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: event.promise
      });
    });
  }
  
  addToQueue(level, args) {
    // Format log entry
    const logEntry = {
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      sessionId: this.sessionId,
      url: window.location.href,
      message: this.formatMessage(args),
      metadata: this.extractMetadata(args),
      userAgent: navigator.userAgent
    };
    
    this.logQueue.push(logEntry);
    
    // Check if we should send immediately
    if (this.logQueue.length >= LOG_BATCH_SIZE) {
      this.flushLogs();
    }
  }
  
  formatMessage(args) {
    // Convert arguments to string message
    return args.map(arg => {
      if (typeof arg === 'object') {
        try {
          return JSON.stringify(arg, null, 2);
        } catch (e) {
          return String(arg);
        }
      }
      return String(arg);
    }).join(' ');
  }
  
  extractMetadata(args) {
    // Extract any object arguments as metadata
    const metadata = {};
    args.forEach((arg, index) => {
      if (typeof arg === 'object' && arg !== null) {
        if (index === args.length - 1 && !Array.isArray(arg)) {
          // Last argument is often metadata object
          Object.assign(metadata, arg);
        }
      }
    });
    return metadata;
  }
  
  startBatchTimer() {
    this.batchTimer = setInterval(() => {
      if (this.logQueue.length > 0) {
        this.flushLogs();
      }
    }, LOG_BATCH_INTERVAL);
  }
  
  loadPendingLogs() {
    try {
      const stored = localStorage.getItem(LOG_STORAGE_KEY);
      if (stored) {
        const pendingLogs = JSON.parse(stored);
        this.logQueue = [...pendingLogs, ...this.logQueue];
        localStorage.removeItem(LOG_STORAGE_KEY);
        this.originalMethods.debug(`Loaded ${pendingLogs.length} pending logs from storage`);
      }
    } catch (e) {
      console.error('Failed to load pending logs:', e);
    }
  }
  
  savePendingLogs() {
    try {
      if (this.logQueue.length > 0) {
        // Limit stored logs to prevent localStorage overflow
        const logsToStore = this.logQueue.slice(-MAX_STORED_LOGS);
        localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(logsToStore));
      }
    } catch (e) {
      console.error('Failed to save pending logs:', e);
    }
  }
  
  async flushLogs(synchronous = false) {
    if (this.isSending || this.logQueue.length === 0) {
      return;
    }
    
    if (!this.isOnline) {
      this.savePendingLogs();
      return;
    }
    
    this.isSending = true;
    const logsToSend = [...this.logQueue];
    this.logQueue = [];
    
    try {
      const sendLogs = async () => {
        const response = await fetch('/api/logs/client', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            logs: logsToSend,
            sessionId: this.sessionId,
            timestamp: new Date().toISOString()
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to send logs: ${response.status}`);
        }
      };
      
      if (synchronous) {
        // Use sendBeacon for synchronous sending on page unload
        const blob = new Blob([JSON.stringify({
          logs: logsToSend,
          sessionId: this.sessionId,
          timestamp: new Date().toISOString()
        })], { type: 'application/json' });
        
        if (navigator.sendBeacon) {
          navigator.sendBeacon('/api/logs/client', blob);
        } else {
          // Fallback to synchronous XHR (deprecated but works)
          const xhr = new XMLHttpRequest();
          xhr.open('POST', '/api/logs/client', false);
          xhr.setRequestHeader('Content-Type', 'application/json');
          xhr.send(JSON.stringify({
            logs: logsToSend,
            sessionId: this.sessionId,
            timestamp: new Date().toISOString()
          }));
        }
      } else {
        await sendLogs();
      }
      
    } catch (error) {
      // Re-add logs to queue on failure
      this.logQueue = [...logsToSend, ...this.logQueue];
      this.savePendingLogs();
      console.error('Failed to send logs to server:', error);
    } finally {
      this.isSending = false;
    }
  }
  
  // Public methods matching loglevel API
  debug(...args) {
    log.debug(...args);
  }
  
  info(...args) {
    log.info(...args);
  }
  
  warn(...args) {
    log.warn(...args);
  }
  
  error(...args) {
    log.error(...args);
  }
  
  // Additional utility methods
  setLevel(level) {
    log.setLevel(level);
    this.info(`Log level changed to: ${level}`);
  }
  
  getLevel() {
    return log.getLevel();
  }
  
  // Performance monitoring
  startTimer(label) {
    const startTime = performance.now();
    return {
      end: (metadata = {}) => {
        const duration = performance.now() - startTime;
        this.debug(`Performance: ${label}`, {
          duration: `${duration.toFixed(2)}ms`,
          ...metadata
        });
        return duration;
      }
    };
  }
  
  // Component lifecycle logging
  logComponentMount(componentName, props = {}) {
    this.debug(`Component mounted: ${componentName}`, { props });
  }
  
  logComponentUnmount(componentName) {
    this.debug(`Component unmounted: ${componentName}`);
  }
  
  logComponentError(componentName, error, errorInfo) {
    this.error(`Component error: ${componentName}`, {
      error: error.toString(),
      stack: error.stack,
      componentStack: errorInfo?.componentStack
    });
  }
  
  // API call logging
  logApiCall(method, url, data = null) {
    this.debug(`API call: ${method} ${url}`, { data });
  }
  
  logApiResponse(method, url, status, duration) {
    const level = status >= 400 ? 'error' : 'debug';
    this[level](`API response: ${method} ${url}`, {
      status,
      duration: `${duration.toFixed(2)}ms`
    });
  }
  
  // User action logging
  logUserAction(action, details = {}) {
    this.info(`User action: ${action}`, details);
  }
  
  // Clean up
  destroy() {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }
    this.flushLogs(true);
  }
}

// Create singleton instance
const logger = new ClientLogger();

/**
 * @typedef {Object} Logger
 * @property {function(...any): void} debug - Log debug messages
 * @property {function(...any): void} info - Log info messages
 * @property {function(...any): void} warn - Log warning messages
 * @property {function(...any): void} error - Log error messages
 * @property {function(string): Object} startTimer - Start a performance timer
 * @property {function(string): void} setLevel - Set the log level
 * @property {function(): string} getLevel - Get current log level
 * @property {function(string, Object=): void} logComponentMount - Log component mount
 * @property {function(string): void} logComponentUnmount - Log component unmount
 * @property {function(string, Error, Object=): void} logComponentError - Log component error
 * @property {function(string, string, any=): void} logApiCall - Log API call
 * @property {function(string, string, number, number): void} logApiResponse - Log API response
 * @property {function(string, Object=): void} logUserAction - Log user action
 * @property {function(): void} destroy - Clean up logger
 */

/** @type {Logger} */
// @ts-ignore
const typedLogger = logger;

// Expose debug control functions for browser console
if (typeof window !== 'undefined') {
  window.logger = logger;
  
  // Global function to enable/disable debug mode
  window.setDebugMode = (enabled) => {
    if (enabled) {
      localStorage.setItem('debug_mode', 'true');
      log.setLevel('debug');
      logger.info('[Logger] Debug mode enabled via console');
    } else {
      localStorage.removeItem('debug_mode');
      // Restore to config level or info
      log.setLevel(logger.configLogLevel || 'info');
      logger.info('[Logger] Debug mode disabled via console');
    }
    return `Debug mode ${enabled ? 'enabled' : 'disabled'}. Refresh page to see full effect.`;
  };
  
  // Helper to check current debug status
  window.getDebugStatus = () => {
    return {
      currentLevel: log.getLevel(),
      configLevel: logger.configLogLevel,
      debugModeEnabled: localStorage.getItem('debug_mode') === 'true',
      urlDebug: new URLSearchParams(window.location.search).get('debug') === 'true'
    };
  };
  
  console.log('%c[Jellynouncer Debug Console]', 'color: #9333ea; font-weight: bold; font-size: 14px');
  console.log('%cDebug commands available:', 'color: #6b7280; font-weight: bold');
  console.log('  setDebugMode(true)  - Enable debug logging');
  console.log('  setDebugMode(false) - Disable debug logging');
  console.log('  getDebugStatus()    - Check current debug settings');
  console.log('  logger              - Access logger instance directly');
}

// Export both the logger instance and the log object for compatibility
/**
 * @type {ClientLogger & Logger}
 * Logger instance with all logging methods:
 * - debug(...args) - Log debug level messages
 * - info(...args) - Log info level messages
 * - warn(...args) - Log warning level messages
 * - error(...args) - Log error level messages
 * - startTimer(label) - Start a performance timer
 * - And more utility methods...
 */
export default logger;
export { log };