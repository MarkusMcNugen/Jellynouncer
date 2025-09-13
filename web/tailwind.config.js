/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Jellyfin brand colors
        jellyfin: {
          purple: '#9b59b6',
          blue: '#3498db',
          gradient: {
            from: '#aa5cc3',
            via: '#7f86ff',
            to: '#00a4dc'
          }
        },
        // Custom color scheme
        primary: {
          50: '#f3f1ff',
          100: '#ebe5ff',
          200: '#d9ceff',
          300: '#bea6ff',
          400: '#9f75ff',
          500: '#843dff',
          600: '#7916ff',
          700: '#6b04fd',
          800: '#5a03d5',
          900: '#4b05ad',
          950: '#2c0076',
        },
        dark: {
          bg: '#0a0a0a',
          surface: '#141414',
          elevated: '#1a1a1a',
          border: '#2a2a2a',
          text: {
            primary: '#ffffff',
            secondary: '#a0a0a0',
            muted: '#666666'
          }
        }
      },
      backgroundImage: {
        'jellyfin-gradient': 'linear-gradient(135deg, #aa5cc3 0%, #7f86ff 50%, #00a4dc 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}