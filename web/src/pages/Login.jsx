import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon, IconDuotone, IconLight } from '../components/FontAwesomeIcon';
import { useAuthStore } from '../stores/authStore';
import logger from '../services/logger';

const Login = () => {
  logger.info('[Login] Component initialization started');
  
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  
  logger.debug('[Login] State hooks initialized', {
    initialStates: {
      loading: false,
      error: null,
      hasUsername: false,
      hasPassword: false
    }
  });
  
  useEffect(() => {
    logger.debug('[Login] Component mounted');
    return () => {
      logger.debug('[Login] Component unmounting');
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    logger.debug('[Login] Form submitted', {
      hasUsername: !!formData.username,
      usernameLength: formData.username.length
      // Never log the actual password
    });
    
    setLoading(true);
    setError(null);

    try {
      logger.debug('[Login] Attempting authentication');
      const success = await login(formData.username, formData.password);
      
      if (success) {
        logger.info('[Login] Authentication successful', {
          username: formData.username
        });
        navigate('/');
      } else {
        logger.warn('[Login] Authentication failed - invalid response');
      }
    } catch (err) {
      logger.error('[Login] Authentication error', {
        message: err.message,
        status: err.response?.status,
        detail: err.response?.data?.detail
        // Never log the password that was attempted
      });
      setError(err.response?.data?.detail || 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    // Only log field changes without sensitive values
    logger.debug('[Login] Form field changed', {
      field: name,
      hasValue: !!value,
      length: value.length
      // Never log the actual password value
    });
    
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex justify-center">
            <div className="bg-purple-600 rounded-full p-3">
              <IconDuotone icon="lock-alt" size="3x" className="text-white" />
            </div>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            Sign in to Jellynouncer
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            Access the web interface management console
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <input type="hidden" name="remember" value="true" />
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="username" className="sr-only">
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <IconLight icon="user" className="text-gray-400" size="lg" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={formData.username}
                  onChange={handleInputChange}
                  className="appearance-none rounded-none relative block w-full px-3 py-2 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10 dark:bg-gray-800 dark:border-gray-700 dark:text-white dark:placeholder-gray-400 sm:text-sm"
                  placeholder="Username"
                />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <IconLight icon="lock" className="text-gray-400" size="lg" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="appearance-none rounded-none relative block w-full px-3 py-2 pl-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-purple-500 focus:border-purple-500 focus:z-10 dark:bg-gray-800 dark:border-gray-700 dark:text-white dark:placeholder-gray-400 sm:text-sm"
                  placeholder="Password"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <IconDuotone icon="exclamation-circle" className="text-red-400" size="lg" aria-hidden="true" />
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                    Authentication failed
                  </h3>
                  <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                    <p>{error}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Authentication is {' '}
              <span className="font-medium text-purple-600 dark:text-purple-400">
                optional by default
              </span>
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
              Enable it in Settings → Security
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;