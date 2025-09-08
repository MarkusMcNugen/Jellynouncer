import { useState, useEffect } from 'react';
import { Icon } from './FontAwesomeIcon';

const DarkModeToggle = () => {
  const [theme, setTheme] = useState(() => {
    // Check localStorage first
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    
    // Then check system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    
    return 'light';
  });

  useEffect(() => {
    // Apply theme to document
    const root = document.documentElement;
    
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    
    // Save to localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => {
      const themes = ['light', 'dark', 'auto'];
      const currentIndex = themes.indexOf(prevTheme);
      const nextIndex = (currentIndex + 1) % themes.length;
      return themes[nextIndex];
    });
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'dark':
        return 'moon';
      case 'light':
        return 'sun';
      case 'auto':
        return 'circle-half-stroke';  // FA7 icon for auto/adjust
      default:
        return 'circle-half-stroke';
    }
  };

  const getThemeColor = () => {
    switch (theme) {
      case 'dark':
        return 'text-purple-400 hover:text-purple-300';
      case 'light':
        return 'text-yellow-500 hover:text-yellow-400';
      case 'auto':
        return 'text-blue-500 hover:text-blue-400';
      default:
        return 'text-gray-500 hover:text-gray-400';
    }
  };

  // Listen for system theme changes when in auto mode
  useEffect(() => {
    if (theme !== 'auto') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      const root = document.documentElement;
      if (e.matches) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };

    // Set initial state for auto mode
    handleChange(mediaQuery);

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [theme]);

  return (
    <button
      onClick={toggleTheme}
      className={`p-2 rounded-lg transition-colors ${getThemeColor()}`}
      title={`Theme: ${theme} (click to toggle)`}
      aria-label="Toggle dark mode"
    >
      <Icon 
        icon={getThemeIcon()} 
        className="w-5 h-5"
      />
    </button>
  );
};

export default DarkModeToggle;