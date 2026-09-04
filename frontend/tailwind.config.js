/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 手账风格配色
        journal: {
          bg: '#faf8f5',
          paper: '#ffffff',
          ink: '#2c2c2c',
          muted: '#8a8a8a',
          accent: '#d4a574',
          accentLight: '#e8d5c0',
          success: '#7fb069',
          warning: '#e8a838',
          danger: '#d4574a',
          primary: '#5b8a72',
        }
      },
      fontFamily: {
        hand: ['"Noto Serif SC"', '"Songti SC"', 'serif'],
      },
    },
  },
  plugins: [],
}
