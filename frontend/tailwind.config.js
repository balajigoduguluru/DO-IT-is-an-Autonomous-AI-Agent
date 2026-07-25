/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        'do-bg-primary': 'var(--do-bg-primary)',
        'do-bg-secondary': 'var(--do-bg-secondary)',
        'do-bg-tertiary': 'var(--do-bg-tertiary)',
        'do-text-primary': 'var(--do-text-primary)',
        'do-text-secondary': 'var(--do-text-secondary)',
        'do-text-tertiary': 'var(--do-text-tertiary)',
        'do-accent': 'var(--do-accent)',
        'do-active': 'var(--do-active)',
        'do-success': 'var(--do-success)',
        'do-warning': 'var(--do-warning)',
        'do-danger': 'var(--do-danger)',
      },
      borderRadius: {
        'do-sm': 'var(--do-radius-sm)',
        'do-md': 'var(--do-radius-md)',
        'do-lg': 'var(--do-radius-lg)',
        'do-full': 'var(--do-radius-full)',
      },
      animation: {
        'shimmer': 'shimmer 1.5s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
};
