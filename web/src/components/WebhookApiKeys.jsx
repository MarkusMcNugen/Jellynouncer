import { useState, useEffect } from 'react';
import { Icon, IconDuotone } from './FontAwesomeIcon';
import logger from '../services/logger';

const WebhookApiKeys = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [keyName, setKeyName] = useState('');
  const [keyDescription, setKeyDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/webhook-keys', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch API keys');
      }

      const data = await response.json();
      setApiKeys(data.keys || []);
      logger.debug('Fetched webhook API keys', { count: data.keys?.length });
    } catch (err) {
      logger.error('Failed to fetch API keys', err);
      setError('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    if (!keyName.trim()) {
      setError('API key name is required');
      return;
    }

    try {
      setCreating(true);
      setError(null);

      const response = await fetch('/api/webhook-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          name: keyName.trim(),
          description: keyDescription.trim()
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create API key');
      }

      const data = await response.json();
      
      // Store the new key for display
      setNewKey(data.key);
      setShowCreateModal(false);
      setShowKeyModal(true);
      
      // Clear form
      setKeyName('');
      setKeyDescription('');
      
      // Refresh the list
      await fetchApiKeys();
      
      logger.info('Created webhook API key', { name: data.name });
    } catch (err) {
      logger.error('Failed to create API key', err);
      setError(err.message || 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevokeKey = async (keyId, keyName) => {
    if (!confirm(`Are you sure you want to revoke the API key "${keyName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/webhook-keys/${keyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to revoke API key');
      }

      // Refresh the list
      await fetchApiKeys();
      
      logger.info('Revoked webhook API key', { id: keyId, name: keyName });
    } catch (err) {
      logger.error('Failed to revoke API key', err);
      alert('Failed to revoke API key');
    }
  };

  const copyToClipboard = async (text) => {
    try {
      // Try the modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        alert('API key copied to clipboard');
        return;
      }
      
      // Fallback method for non-HTTPS or older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        const successful = document.execCommand('copy');
        if (successful) {
          alert('API key copied to clipboard');
        } else {
          throw new Error('Copy command failed');
        }
      } catch (err) {
        // If copy still fails, show the key in a prompt for manual copying
        prompt('Failed to copy automatically. Please copy the API key manually:', text);
      } finally {
        document.body.removeChild(textArea);
      }
    } catch (err) {
      logger.error('Failed to copy to clipboard', err);
      // Show the key in a prompt as last resort
      prompt('Failed to copy automatically. Please copy the API key manually:', text);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Webhook API Keys
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            API keys for authenticating webhook requests from Jellyfin
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors flex items-center gap-2"
        >
          <Icon icon="plus" />
          Generate New API Key
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* API Keys List */}
      {apiKeys.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-8 text-center">
          <IconDuotone icon="key" size="3x" className="text-gray-400 dark:text-gray-600 mb-4" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No API keys have been created yet
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mb-6">
            Generate an API key to authenticate webhook requests from Jellyfin
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          >
            Generate Your First API Key
          </button>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Last Used
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Usage
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {apiKeys.map((key) => (
                <tr key={key.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {key.name}
                      </div>
                      {key.description && (
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {key.description}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    {formatDate(key.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    <div>
                      {formatDate(key.last_used)}
                      {key.last_ip && (
                        <div className="text-xs text-gray-500 dark:text-gray-500">
                          from {key.last_ip}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    {key.usage_count || 0} requests
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => handleRevokeKey(key.id, key.name)}
                      className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Jellyfin Configuration Help */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2 flex items-center gap-2">
          <Icon icon="circle-info" />
          How to Configure Jellyfin Webhook Plugin
        </h4>
        <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-2 ml-6">
          <li>1. Generate an API key using the button above</li>
          <li>2. In Jellyfin, go to Dashboard → Plugins → Webhook → Settings</li>
          <li>3. Add a new webhook destination with URL: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">http://your-server:1984/webhook</code></li>
          <li>4. Add a custom request header:
            <div className="mt-1 ml-4">
              <div>Key: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">Authorization</code></div>
              <div>Value: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">ApiKey YOUR_API_KEY_HERE</code></div>
            </div>
          </li>
          <li>5. Enable the notification types you want to receive</li>
        </ol>
      </div>

      {/* Create API Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Generate New API Key
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g., Jellyfin Server"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  autoFocus
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description (Optional)
                </label>
                <input
                  type="text"
                  value={keyDescription}
                  onChange={(e) => setKeyDescription(e.target.value)}
                  placeholder="e.g., Main Jellyfin instance webhook"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-2">
                  <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
                </div>
              )}
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setKeyName('');
                  setKeyDescription('');
                  setError(null);
                }}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateKey}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                disabled={creating || !keyName.trim()}
              >
                {creating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Creating...
                  </>
                ) : (
                  <>
                    <Icon icon="key" />
                    Generate API Key
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Show New API Key Modal */}
      {showKeyModal && newKey && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-green-100 dark:bg-green-900/30 rounded-full p-2">
                <Icon icon="check-circle" className="text-green-600 dark:text-green-400" size="lg" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                API Key Generated Successfully
              </h3>
            </div>
            
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-3 mb-4">
              <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
                ⚠️ Important: Save this API key now - it won't be shown again!
              </p>
            </div>
            
            <div className="bg-gray-50 dark:bg-gray-900 rounded-md p-4 mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Your API Key:
              </label>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-mono text-gray-900 dark:text-white select-all">
                  ApiKey {newKey}
                </code>
                <button
                  onClick={() => copyToClipboard(`ApiKey ${newKey}`)}
                  className="px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  <Icon icon="copy" />
                </button>
              </div>
            </div>
            
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-md p-4 mb-4">
              <p className="text-sm text-blue-800 dark:text-blue-300 font-medium mb-2">
                Add this to Jellyfin Webhook Plugin:
              </p>
              <div className="text-sm text-blue-700 dark:text-blue-200 space-y-1">
                <div>Header Key: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">Authorization</code></div>
                <div>Header Value: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">ApiKey {newKey}</code></div>
              </div>
            </div>
            
            <div className="flex justify-end">
              <button
                onClick={() => {
                  setShowKeyModal(false);
                  setNewKey(null);
                }}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WebhookApiKeys;