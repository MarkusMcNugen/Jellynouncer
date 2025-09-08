import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import withLifecycleLogging from '../utils/withLifecycleLogging'
import { apiService } from '../services/api'
import logger from '../services/logger'

function Backups() {
  const navigate = useNavigate()
  const { isAuthenticated, authEnabled } = useAuthStore()
  
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [backupStatus, setBackupStatus] = useState(null)
  const [backupList, setBackupList] = useState([])
  const [config, setConfig] = useState({})
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [restoreComponents, setRestoreComponents] = useState({
    config: true,
    database: true,
    templates: true,
    ssl: false,
    logs: false
  })
  const [activeTab, setActiveTab] = useState('status')
  const [createDescription, setCreateDescription] = useState('')
  
  // Check authentication
  useEffect(() => {
    if (authEnabled && !isAuthenticated) {
      logger.warn('User not authenticated, redirecting to login')
      navigate('/login')
    }
  }, [authEnabled, isAuthenticated, navigate])
  
  // Load backup status and list
  useEffect(() => {
    fetchBackupData()
  }, [])
  
  const fetchBackupData = async () => {
    try {
      setLoading(true)
      logger.debug('Fetching backup data')
      
      // Fetch backup status
      const statusResponse = await apiService.get('/backup/status')
      logger.debug('Backup status response:', statusResponse.data)
      setBackupStatus(statusResponse.data)
      setConfig(statusResponse.data.config || {})
      
      // Fetch backup list
      const listResponse = await apiService.get('/backup/list')
      logger.debug('Backup list response:', listResponse.data)
      setBackupList(listResponse.data.backups || [])
    } catch (error) {
      logger.error('Failed to fetch backup data:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleConfigChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }))
  }
  
  const saveConfig = async () => {
    try {
      setSaving(true)
      logger.debug('Saving backup configuration:', config)
      
      await apiService.put('/backup/config', config)
      logger.info('Backup configuration saved successfully')
      
      // Refresh status
      await fetchBackupData()
    } catch (error) {
      logger.error('Failed to save backup configuration:', error)
      alert('Failed to save configuration: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSaving(false)
    }
  }
  
  const createBackup = async () => {
    try {
      setSaving(true)
      logger.debug('Creating manual backup')
      
      const formData = new FormData()
      formData.append('description', createDescription || 'Manual backup')
      
      const response = await apiService.post('/backup/create', formData)
      logger.info('Backup created successfully:', response.data)
      
      alert('Backup created successfully: ' + response.data.backup.filename)
      setCreateDescription('')
      
      // Refresh list
      await fetchBackupData()
    } catch (error) {
      logger.error('Failed to create backup:', error)
      alert('Failed to create backup: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSaving(false)
    }
  }
  
  const restoreBackup = async () => {
    if (!selectedBackup) {
      alert('Please select a backup to restore')
      return
    }
    
    if (!confirm(`Are you sure you want to restore from ${selectedBackup}? This will overwrite current data.`)) {
      return
    }
    
    try {
      setSaving(true)
      logger.debug('Restoring backup:', selectedBackup)
      
      const components = Object.keys(restoreComponents).filter(key => restoreComponents[key])
      const response = await apiService.post(`/backup/restore/${selectedBackup}`, null, {
        params: { components }
      })
      
      logger.info('Backup restored successfully:', response.data)
      alert('Backup restored successfully. You may need to restart the application for changes to take effect.')
      
      // Refresh data
      await fetchBackupData()
    } catch (error) {
      logger.error('Failed to restore backup:', error)
      alert('Failed to restore backup: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSaving(false)
    }
  }
  
  const deleteBackup = async (backupName) => {
    if (!confirm(`Are you sure you want to delete ${backupName}?`)) {
      return
    }
    
    try {
      logger.debug('Deleting backup:', backupName)
      
      await apiService.delete(`/backup/${backupName}`)
      logger.info('Backup deleted successfully')
      
      // Refresh list
      await fetchBackupData()
    } catch (error) {
      logger.error('Failed to delete backup:', error)
      alert('Failed to delete backup: ' + (error.response?.data?.detail || error.message))
    }
  }
  
  const testBackupSystem = async () => {
    try {
      setSaving(true)
      logger.debug('Testing backup system')
      
      const response = await apiService.post('/backup/test')
      logger.info('Backup system test completed:', response.data)
      
      alert('Backup system test completed successfully!')
    } catch (error) {
      logger.error('Backup system test failed:', error)
      alert('Backup system test failed: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSaving(false)
    }
  }
  
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
  
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading backup system...</div>
      </div>
    )
  }
  
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Backup Management</h1>
      
      {/* Tab Navigation */}
      <div className="border-b border-gray-700 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('status')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'status'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Status
          </button>
          <button
            onClick={() => setActiveTab('backups')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'backups'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Backups ({backupList.length})
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'settings'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Settings
          </button>
          <button
            onClick={() => setActiveTab('restore')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'restore'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Restore
          </button>
        </nav>
      </div>
      
      {/* Status Tab */}
      {activeTab === 'status' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">System Status</h2>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-gray-400">Backup System</p>
                <p className="text-lg font-medium">
                  {backupStatus?.enabled ? (
                    <span className="text-green-500">Enabled</span>
                  ) : (
                    <span className="text-red-500">Disabled</span>
                  )}
                </p>
              </div>
              
              <div>
                <p className="text-gray-400">Schedule</p>
                <p className="text-lg font-medium capitalize">
                  {config.schedule || 'Not configured'}
                </p>
              </div>
              
              <div>
                <p className="text-gray-400">Next Backup</p>
                <p className="text-lg font-medium">
                  {backupStatus?.next_backup ? formatDate(backupStatus.next_backup) : 'N/A'}
                </p>
              </div>
              
              <div>
                <p className="text-gray-400">Estimated Size</p>
                <p className="text-lg font-medium">
                  {backupStatus?.estimated_size_mb || 0} MB
                </p>
              </div>
              
              <div>
                <p className="text-gray-400">Total Backups</p>
                <p className="text-lg font-medium">
                  {backupList.length}
                </p>
              </div>
              
              <div>
                <p className="text-gray-400">Max Backups</p>
                <p className="text-lg font-medium">
                  {config.max_backups || 10}
                </p>
              </div>
            </div>
            
            <div className="mt-6 flex space-x-4">
              <button
                onClick={createBackup}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Create Backup Now
              </button>
              
              <button
                onClick={testBackupSystem}
                disabled={saving}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
              >
                Test System
              </button>
            </div>
            
            {/* Create Backup Description */}
            <div className="mt-4">
              <input
                type="text"
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="Backup description (optional)"
                className="w-full px-3 py-2 bg-gray-700 rounded"
              />
            </div>
          </div>
        </div>
      )}
      
      {/* Backups Tab */}
      {activeTab === 'backups' && (
        <div className="space-y-4">
          {backupList.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-6 text-center">
              <p className="text-gray-400">No backups found</p>
            </div>
          ) : (
            backupList.map((backup) => (
              <div key={backup.filename} className="bg-gray-800 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold">{backup.filename}</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      Created: {formatDate(backup.created_at)}
                    </p>
                    <p className="text-sm text-gray-400">
                      Size: {formatBytes(backup.size)}
                    </p>
                    {backup.description && (
                      <p className="text-sm text-gray-400">
                        Description: {backup.description}
                      </p>
                    )}
                    <p className="text-sm text-gray-400">
                      Type: {backup.backup_type || 'manual'}
                    </p>
                  </div>
                  
                  <div className="flex space-x-2">
                    <button
                      onClick={() => {
                        setSelectedBackup(backup.filename)
                        setActiveTab('restore')
                      }}
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                    >
                      Restore
                    </button>
                    
                    <button
                      onClick={() => deleteBackup(backup.filename)}
                      className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
      
      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Backup Settings</h2>
            
            <div className="space-y-4">
              <div>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={config.enabled}
                    onChange={(e) => handleConfigChange('enabled', e.target.checked)}
                    className="rounded"
                  />
                  <span>Enable automatic backups</span>
                </label>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Schedule</label>
                <select
                  value={config.schedule}
                  onChange={(e) => handleConfigChange('schedule', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 rounded"
                >
                  <option value="disabled">Disabled</option>
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
              
              {config.schedule === 'daily' && (
                <div>
                  <label className="block text-sm font-medium mb-1">Backup Time</label>
                  <input
                    type="time"
                    value={config.backup_time}
                    onChange={(e) => handleConfigChange('backup_time', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 rounded"
                  />
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium mb-1">Retention Days</label>
                <input
                  type="number"
                  value={config.retention_days}
                  onChange={(e) => handleConfigChange('retention_days', parseInt(e.target.value))}
                  min="1"
                  className="w-full px-3 py-2 bg-gray-700 rounded"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Max Backups</label>
                <input
                  type="number"
                  value={config.max_backups}
                  onChange={(e) => handleConfigChange('max_backups', parseInt(e.target.value))}
                  min="1"
                  className="w-full px-3 py-2 bg-gray-700 rounded"
                />
              </div>
              
              <div>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={config.compress}
                    onChange={(e) => handleConfigChange('compress', e.target.checked)}
                    className="rounded"
                  />
                  <span>Compress backups</span>
                </label>
              </div>
              
              <div className="border-t border-gray-700 pt-4">
                <h3 className="font-medium mb-2">Components to Backup</h3>
                
                <div className="space-y-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.backup_config}
                      onChange={(e) => handleConfigChange('backup_config', e.target.checked)}
                      className="rounded"
                    />
                    <span>Configuration files</span>
                  </label>
                  
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.backup_database}
                      onChange={(e) => handleConfigChange('backup_database', e.target.checked)}
                      className="rounded"
                    />
                    <span>Database</span>
                  </label>
                  
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.backup_templates}
                      onChange={(e) => handleConfigChange('backup_templates', e.target.checked)}
                      className="rounded"
                    />
                    <span>Notification templates</span>
                  </label>
                  
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.backup_ssl}
                      onChange={(e) => handleConfigChange('backup_ssl', e.target.checked)}
                      className="rounded"
                    />
                    <span>SSL certificates</span>
                  </label>
                  
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.backup_logs}
                      onChange={(e) => handleConfigChange('backup_logs', e.target.checked)}
                      className="rounded"
                    />
                    <span>Log files</span>
                  </label>
                </div>
              </div>
              
              <div className="flex justify-end">
                <button
                  onClick={saveConfig}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Restore Tab */}
      {activeTab === 'restore' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Restore from Backup</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Select Backup</label>
                <select
                  value={selectedBackup || ''}
                  onChange={(e) => setSelectedBackup(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 rounded"
                >
                  <option value="">Choose a backup...</option>
                  {backupList.map((backup) => (
                    <option key={backup.filename} value={backup.filename}>
                      {backup.filename} ({formatBytes(backup.size)}) - {formatDate(backup.created_at)}
                    </option>
                  ))}
                </select>
              </div>
              
              {selectedBackup && (
                <>
                  <div className="border-t border-gray-700 pt-4">
                    <h3 className="font-medium mb-2">Components to Restore</h3>
                    
                    <div className="space-y-2">
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={restoreComponents.config}
                          onChange={(e) => setRestoreComponents(prev => ({
                            ...prev,
                            config: e.target.checked
                          }))}
                          className="rounded"
                        />
                        <span>Configuration files</span>
                      </label>
                      
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={restoreComponents.database}
                          onChange={(e) => setRestoreComponents(prev => ({
                            ...prev,
                            database: e.target.checked
                          }))}
                          className="rounded"
                        />
                        <span>Database</span>
                      </label>
                      
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={restoreComponents.templates}
                          onChange={(e) => setRestoreComponents(prev => ({
                            ...prev,
                            templates: e.target.checked
                          }))}
                          className="rounded"
                        />
                        <span>Notification templates</span>
                      </label>
                      
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={restoreComponents.ssl}
                          onChange={(e) => setRestoreComponents(prev => ({
                            ...prev,
                            ssl: e.target.checked
                          }))}
                          className="rounded"
                        />
                        <span>SSL certificates</span>
                      </label>
                      
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={restoreComponents.logs}
                          onChange={(e) => setRestoreComponents(prev => ({
                            ...prev,
                            logs: e.target.checked
                          }))}
                          className="rounded"
                        />
                        <span>Log files</span>
                      </label>
                    </div>
                  </div>
                  
                  <div className="bg-yellow-800 bg-opacity-50 rounded-lg p-4">
                    <p className="text-yellow-300 font-medium">⚠️ Warning</p>
                    <p className="text-sm mt-1">
                      Restoring will overwrite current data with the selected backup. 
                      A pre-restore backup will be created automatically before the restore operation.
                    </p>
                  </div>
                  
                  <div className="flex justify-end">
                    <button
                      onClick={restoreBackup}
                      disabled={saving}
                      className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                    >
                      {saving ? 'Restoring...' : 'Restore Backup'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const BackupsWithLogging = withLifecycleLogging(Backups, 'Backups')
export default BackupsWithLogging