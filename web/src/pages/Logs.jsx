import { useState, useRef, useMemo, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiService } from '../services/api'
import { IconDuotone, IconLight } from '../components/FontAwesomeIcon'
import { parseLogText, filterLogs, getLogStatistics, formatLogForDisplay, exportLogs, LOG_LEVEL_COLORS } from '../utils/logParser'
import { VariableSizeList as VirtualList } from 'react-window'
import logger from '../services/logger'
// Removed unused lucide-react import - using FontAwesome icons instead

const Logs = () => {
  logger.info('[Logs] Component initialization started');
  
  const [logFile, setLogFile] = useState('jellynouncer.log')
  const [lines, setLines] = useState(500)
  const [availableLogFiles, setAvailableLogFiles] = useState([])
  const [level, setLevel] = useState('')
  const [component, setComponent] = useState('')
  const [search, setSearch] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [showStats] = useState(true) // Could be toggled in future
  
  logger.debug('[Logs] State hooks initialized', {
    initialStates: {
      logFile: 'jellynouncer.log',
      lines: 500,
      level: '',
      component: '',
      search: '',
      autoRefresh: true,
      showStats: true
    }
  })
  
  const listRef = useRef(null)
  const rowHeights = useRef({})
  const measuredRows = useRef(new Set())
  const resizeObserver = useRef(null)
  const containerRef = useRef(null)
  
  // Default estimated height for unmeasured rows
  const estimatedRowHeight = 60
  
  // Initialize ResizeObserver
  useEffect(() => {
    resizeObserver.current = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        const index = parseInt(entry.target.dataset.index, 10)
        if (!isNaN(index)) {
          const newHeight = entry.contentRect.height
          if (rowHeights.current[index] !== newHeight) {
            rowHeights.current[index] = newHeight
            // Reset the list cache for this item
            if (listRef.current) {
              listRef.current.resetAfterIndex(index)
            }
          }
        }
      })
    })
    
    return () => {
      if (resizeObserver.current) {
        resizeObserver.current.disconnect()
      }
    }
  }, [])
  
  // This effect will be moved after parsedLogs is defined
  
  // Handle window resize to recalculate wrapped text
  useEffect(() => {
    const handleResize = () => {
      // Clear all measurements on resize since text wrapping may change
      rowHeights.current = {}
      measuredRows.current.clear()
      if (listRef.current) {
        listRef.current.resetAfterIndex(0)
      }
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  
  // Get item size with measurement
  const getItemSize = useCallback((index) => {
    return rowHeights.current[index] || estimatedRowHeight
  }, [])
  
  // Fetch available log files on component mount
  useEffect(() => {
    logger.debug('[Logs] Fetching available log files');
    
    apiService.getLogFiles()
      .then(response => {
        const files = response.data?.files || [];
        setAvailableLogFiles(files);
        
        logger.info('[Logs] Available log files loaded', { 
          count: files.length,
          files: files.map(f => ({ name: f.name, size: f.size }))
        });
        
        // If current file doesn't exist in list, switch to first available
        if (files.length > 0 && !files.find(f => f.name === logFile)) {
          logger.debug('[Logs] Switching to first available log file', {
            from: logFile,
            to: files[0].name
          });
          setLogFile(files[0].name);
        }
      })
      .catch(err => {
        logger.error('[Logs] Failed to fetch available log files', {
          message: err.message,
          response: err.response?.data
        });
      });
      
    return () => {
      logger.debug('[Logs] Component unmounting');
    };
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  
  // Fetch logs - now using raw logs endpoint for better multi-line support
  const { data: logsResponse, refetch, isLoading } = useQuery({
    queryKey: ['logs', logFile, lines, level, component, search],
    queryFn: async () => {
      const fetchTimer = logger.startTimer('[Logs] Fetch log data');
      logger.debug('[Logs] Fetching raw logs', {
        file: logFile,
        lines,
        filters: {
          level: level || 'none',
          component: component || 'none',
          search: search || 'none'
        }
      });
      
      try {
        const result = await apiService.getRawLogs({
          file: logFile,
          lines,
          level: level || undefined,
          component: component || undefined,
          search: search || undefined
        });
        
        logger.info('[Logs] Raw log data received', {
          dataType: result?.data?.type,
          contentLength: result?.data?.content?.length || 0,
          hasData: !!result?.data,
          linesReturned: result?.data?.content?.split('\n').length || 0
        });
        
        fetchTimer.end();
        return result;
      } catch (err) {
        logger.error('[Logs] Failed to fetch logs', {
          message: err.message,
          response: err.response?.data,
          file: logFile
        });
        throw err;
      }
    },
    refetchInterval: autoRefresh ? 5000 : false
  })
  
  // Parse and filter logs
  const { parsedLogs, stats } = useMemo(() => {
    const parseTimer = logger.startTimer('[Logs] Parse and filter logs');
    
    if (!logsResponse?.data) {
      logger.debug('[Logs] No log data to parse');
      return { parsedLogs: [], stats: {} }
    }
    
    let logText = '';
    
    // We now always get raw content from the new endpoint
    if (logsResponse.data.type === 'raw' && logsResponse.data.content) {
      // Raw content from our new endpoint
      logText = logsResponse.data.content;
    } else if (typeof logsResponse.data === 'string') {
      // Fallback: Raw log text - use directly
      logText = logsResponse.data;
    } else if (logsResponse.data.content) {
      // Fallback: Raw content field
      logText = logsResponse.data.content;
    } else if (logsResponse.data.logs && Array.isArray(logsResponse.data.logs)) {
      // Fallback: Pre-parsed logs - reconstruct (this will lose multi-line formatting)
      console.warn('Using pre-parsed logs - multi-line entries may not display correctly');
      logText = logsResponse.data.logs.map(log => 
        `[${log.timestamp}][${log.level}][${log.component}] ${log.message}`
      ).join('\n');
    }
    
    const parsed = parseLogText(logText)
    const filtered = filterLogs(parsed, { level, component, search })
    // Reverse the logs to show most recent first
    const reversed = filtered.slice().reverse()
    const statistics = getLogStatistics(filtered)
    
    logger.debug('[Logs] Parsing complete', {
      rawLines: logText.split('\n').length,
      parsedCount: parsed.length,
      filteredCount: filtered.length,
      statistics: {
        errors: statistics.error || 0,
        warnings: statistics.warning || 0,
        info: statistics.info || 0,
        debug: statistics.debug || 0
      }
    });
    
    parseTimer.end();
    return { parsedLogs: reversed, stats: statistics }
  }, [logsResponse, level, component, search])
  
  // Clear measurements when logs change
  useEffect(() => {
    rowHeights.current = {}
    measuredRows.current.clear()
    if (listRef.current) {
      listRef.current.resetAfterIndex(0)
    }
  }, [parsedLogs])
  
  // Get log level icon
  const getLevelIcon = (level) => {
    switch(level) {
      case 'ERROR':
      case 'CRITICAL':
      case 'FATAL':
        return <IconDuotone icon="circle-exclamation" size="xs" className="text-red-500" />
      case 'WARNING':
      case 'WARN':
        return <IconDuotone icon="triangle-exclamation" size="xs" className="text-yellow-500" />
      case 'INFO':
        return <IconDuotone icon="circle-info" size="xs" className="text-blue-500" />
      case 'DEBUG':
        return <IconDuotone icon="bug" size="xs" className="text-gray-500" />
      default:
        return null
    }
  }
  
  // Row renderer for virtual list with measurement
  const LogRow = ({ index, style }) => {
    const log = parsedLogs[index]
    const rowRef = useRef(null)
    
    useEffect(() => {
      const currentRowRef = rowRef.current
      
      if (currentRowRef && !measuredRows.current.has(index)) {
        // Measure the actual height of the row
        const height = currentRowRef.getBoundingClientRect().height
        if (height > 0) {
          measuredRows.current.add(index)
          if (rowHeights.current[index] !== height) {
            rowHeights.current[index] = height
            // Observe for future changes
            if (resizeObserver.current) {
              resizeObserver.current.observe(currentRowRef)
            }
            // Update the list if height changed
            if (listRef.current) {
              listRef.current.resetAfterIndex(index)
            }
          }
        }
      }
      
      return () => {
        // Cleanup observer when row unmounts
        if (currentRowRef && resizeObserver.current) {
          resizeObserver.current.unobserve(currentRowRef)
        }
      }
    }, [index, log])
    
    if (!log) return null
    
    if (log.type !== 'log') {
      return (
        <div 
          ref={rowRef}
          data-index={index}
          style={Object.assign({}, style, { height: 'auto' })}
          className="flex items-center px-4 py-1 font-mono text-xs text-dark-text-muted"
        >
          {log.text}
        </div>
      )
    }
    
    const formatted = formatLogForDisplay(log, { 
      showTimestamp: true, 
      showComponent: true,
      highlightSearch: search 
    })
    
    // Process the message HTML outside of JSX
    let processedMessage = log.message
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
    
    // Then apply search highlighting if needed
    if (search) {
      processedMessage = processedMessage.replace(
        new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
        '<mark style="background-color: rgba(251, 191, 36, 0.3); color: rgb(254, 240, 138);">$1</mark>'
      );
    }
    
    // Convert newlines to <br> tags for proper display
    processedMessage = processedMessage.replace(/\r\n/g, '<br>');
    processedMessage = processedMessage.replace(/\n/g, '<br>');
    processedMessage = processedMessage.replace(/\r/g, '<br>');
    
    return (
      <div 
        ref={rowRef}
        data-index={index}
        style={Object.assign({}, style, { height: 'auto' })}
        className={`flex items-start gap-2 px-4 py-2 hover:bg-dark-elevated/50 transition-colors ${formatted.rowClassName}`}
      >
        {/* Timestamp */}
        <span className="text-xs text-dark-text-muted font-mono min-w-[180px] flex-shrink-0">
          {log.timestamp}
        </span>
        
        {/* Level */}
        <span 
          className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold min-w-[80px] justify-center flex-shrink-0"
          style={Object.assign({}, {
            color: formatted.level.color,
            backgroundColor: formatted.level.bgColor 
          })}
        >
          {getLevelIcon(log.level)}
          {log.level}
        </span>
        
        {/* Component */}
        <span className="text-xs text-jellyfin-purple font-mono min-w-[200px] flex-shrink-0 truncate">
          [{log.component}]
        </span>
        
        {/* Message - preserving leading spaces and proper overflow handling */}
        <span 
          className="flex-1 text-sm font-mono text-dark-text-primary break-all whitespace-pre-wrap overflow-wrap-anywhere"
          style={Object.assign({}, { wordBreak: 'break-word' })}
          dangerouslySetInnerHTML={Object.assign({}, { __html: processedMessage })}
        />
      </div>
    )
  }
  
  // Export logs handler
  const handleExport = (format) => {
    const exported = exportLogs(parsedLogs, format)
    const blob = new Blob([exported], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `jellynouncer-logs-${new Date().toISOString()}.${format}`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  return (
    <div className="h-full flex flex-col -mx-4 sm:-mx-6 lg:-mx-8">
      {/* Header */}
      <div className="px-4 py-4 border-b border-dark-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Log Viewer</h2>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input 
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto-refresh
            </label>
            <button 
              onClick={() => refetch()}
              className="btn btn-secondary"
              disabled={isLoading}
            >
              <IconDuotone icon="arrows-rotate" spin={isLoading} />
            </button>
          </div>
        </div>
        
        {/* Filters */}
        <div className="flex gap-3">
          <select 
            className="input"
            value={logFile}
            onChange={(e) => setLogFile(e.target.value)}
          >
            {availableLogFiles.length > 0 ? (
              availableLogFiles.map(file => (
                <option key={file.name} value={file.name}>
                  {file.name} ({file.size_readable})
                </option>
              ))
            ) : (
              <option value="jellynouncer.log">jellynouncer.log</option>
            )}
          </select>
          
          <select 
            className="input"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            <option value="">All Levels</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
          
          <input 
            type="text"
            className="input"
            placeholder="Filter by component..."
            value={component}
            onChange={(e) => setComponent(e.target.value)}
          />
          
          <div className="flex-1 relative">
            <IconLight icon="magnifying-glass" className="absolute left-3 top-1/2 transform -translate-y-1/2 text-dark-text-muted" size="lg" />
            <input 
              type="text"
              className="input pl-10 w-full"
              placeholder="Search logs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          <select 
            className="input"
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
          >
            <option value={100}>Last 100</option>
            <option value={500}>Last 500</option>
            <option value={1000}>Last 1000</option>
            <option value={5000}>Last 5000</option>
          </select>
          
          <div className="relative group">
            <button className="btn btn-secondary flex items-center gap-2">
              <IconDuotone icon="download" size="sm" />
              Export
              <IconLight icon="chevron-down" size="xs" />
            </button>
            <div className="absolute right-0 mt-1 w-32 bg-dark-elevated rounded-lg shadow-lg hidden group-hover:block z-10">
              <button 
                onClick={() => handleExport('txt')}
                className="w-full px-4 py-2 text-left hover:bg-dark-border text-sm"
              >
                Text (.txt)
              </button>
              <button 
                onClick={() => handleExport('json')}
                className="w-full px-4 py-2 text-left hover:bg-dark-border text-sm"
              >
                JSON (.json)
              </button>
              <button 
                onClick={() => handleExport('csv')}
                className="w-full px-4 py-2 text-left hover:bg-dark-border text-sm"
              >
                CSV (.csv)
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Statistics Bar */}
      {showStats && stats.total > 0 && (
        <div className="px-4 py-2 bg-dark-elevated border-b border-dark-border">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-dark-text-muted">Total:</span>
              <span className="font-semibold">{stats.total}</span>
            </div>
            
            {Object.entries(LOG_LEVEL_COLORS).map(([levelName, levelStyle]) => {
              const count = stats.byLevel[levelName] || 0
              if (count === 0) return null
              
              return (
                <div key={levelName} className="flex items-center gap-2">
                  <span 
                    className="px-2 py-0.5 rounded text-xs font-bold"
                    style={Object.assign({}, {
                      color: levelStyle.color,
                      backgroundColor: levelStyle.bgColor 
                    })}
                  >
                    {levelName}
                  </span>
                  <span className="font-semibold">{count}</span>
                </div>
              )
            })}
            
            {stats.errorCount > 0 && (
              <div className="flex items-center gap-2 text-red-500">
                <IconDuotone icon="circle-exclamation" size="xs" />
                <span>{stats.errorCount} errors</span>
              </div>
            )}
            
            {stats.warningCount > 0 && (
              <div className="flex items-center gap-2 text-yellow-500">
                <IconDuotone icon="triangle-exclamation" size="xs" />
                <span>{stats.warningCount} warnings</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Log Viewer */}
      <div className="flex-1 bg-dark-bg overflow-hidden px-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="spinner"></div>
          </div>
        ) : parsedLogs.length > 0 ? (
          <div ref={containerRef} className="h-full w-full">
            <VirtualList
              ref={listRef}
              height={window.innerHeight - 200} // Adjust based on header height
              itemCount={parsedLogs.length}
              itemSize={getItemSize}
              estimatedItemSize={estimatedRowHeight}
              width="100%"
              className="scrollbar-thin scrollbar-thumb-dark-border scrollbar-track-dark-surface"
              style={Object.assign({}, { overflowX: 'hidden' })}
              overscanCount={3} // Render a few extra items for smoother scrolling
            >
              {LogRow}
            </VirtualList>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <IconLight icon="circle-info" size="3x" className="text-dark-text-muted mx-auto mb-4" />
              <p className="text-dark-text-secondary">No logs found</p>
              <p className="text-sm text-dark-text-muted mt-2">
                Try adjusting your filters or refreshing
              </p>
            </div>
          </div>
        )}
      </div>
      
      {/* Recent Errors Panel (if any) */}
      {stats.recentErrors && stats.recentErrors.length > 0 && (
        <div className="p-4 bg-red-900/20 border-t border-red-500/30">
          <h3 className="text-sm font-semibold text-red-400 mb-2">Recent Errors</h3>
          <div className="space-y-1">
            {stats.recentErrors.slice(0, 3).map((error, index) => (
              <div key={index} className="text-xs">
                <span className="text-dark-text-muted">{error.timestamp}</span>
                <span className="text-red-400 ml-2">[{error.component}]</span>
                <span className="text-dark-text-primary ml-2">{error.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Logs