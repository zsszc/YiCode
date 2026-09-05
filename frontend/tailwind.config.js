/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 现代深色主题（journal-* 命名保留兼容，语义已映射为深色）
        journal: {
          bg: '#0b0e14',
          paper: '#131722',
          ink: '#e8eaf2',
          muted: '#8b93a9',
          accent: '#7c6cf0',
          accentLight: '#2a2745',
          success: '#34d399',
          warning: '#fbbf24',
          danger: '#f87171',
          primary: '#7c6cf0',
        },
        // 新增语义色
        surface: {
          DEFAULT: '#131722',
          raised: '#1a2030',
          hover: '#212941',
        },
        line: '#232a3d',
        brand: {
          DEFAULT: '#7c6cf0',
          light: '#a99dff',
          dim: '#2a2745',
        },
        easy: '#34d399',
        medium: '#fbbf24',
        hard: '#f87171',
      },
      fontFamily: {
        hand: ['"Noto Serif SC"', '"Songti SC"', 'serif'],
        sans: ['"Inter"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 24px rgba(124, 108, 240, 0.25)',
        card: '0 4px 24px rgba(0, 0, 0, 0.35)',
      },
    },
  },
  plugins: [],
}
