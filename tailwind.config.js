/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        danger: '#ef4444',
        warning: '#f59e0b',
        success: '#10b981',
        critical: '#b91c1c',
        primary: '#0f172a',
        accent: '#2563eb',
      },
    },
  },
  plugins: [],
}
