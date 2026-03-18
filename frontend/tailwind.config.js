/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#020617',
          900: '#0f172a',
          800: '#1e293b',
        },
      },
      boxShadow: {
        panel: '0 10px 40px -15px rgba(15, 23, 42, 0.75)',
      },
    },
  },
  plugins: [],
}

