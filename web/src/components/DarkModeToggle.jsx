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
    
    // Simple logic - if theme is 'dark', add dark class, otherwise remove it
    if (theme === 'dark') {
      root.classList.add('dark');
      console.log('[DarkModeToggle] Applied dark mode');
    } else {
      root.classList.remove('dark');
      console.log('[DarkModeToggle] Applied light mode');
    }
    
    // Save to localStorage
    localStorage.setItem('theme', theme);
    console.log('[DarkModeToggle] Theme saved:', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => {
      // Only toggle between light and dark for explicit control
      // Remove 'auto' to prevent browser preference override
      const themes = ['light', 'dark'];
      const currentIndex = themes.indexOf(prevTheme === 'auto' ? 'light' : prevTheme);
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

  // Debug: log theme changes
  useEffect(() => {
    console.log('[DarkModeToggle] Current theme:', theme);
    const root = document.documentElement;
    console.log('[DarkModeToggle] Document classes:', root.className);
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