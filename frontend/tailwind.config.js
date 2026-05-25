/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 主色调
        primary: {
          DEFAULT: '#3B82F6',
          hover: '#2563EB',
          light: '#60A5FA',
        },
        // 背景色
        bg: {
          primary: '#0F172A',
          secondary: '#1E293B',
          tertiary: '#334155',
        },
        // 文本色
        text: {
          primary: '#F8FAFC',
          secondary: '#CBD5E1',
          muted: '#64748B',
        },
        // 边框色
        border: {
          primary: '#334155',
          secondary: '#475569',
        },
        // 功能色
        success: '#22C55E',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#06B6D4',
        // 节点状态色
        node: {
          pending: '#64748B',
          running: '#3B82F6',
          completed: '#22C55E',
          error: '#EF4444',
          warning: '#F59E0B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      backdropBlur: {
        glass: '12px',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        node: '0 4px 12px rgba(0, 0, 0, 0.15)',
        'node-hover': '0 8px 24px rgba(0, 0, 0, 0.25)',
      },
    },
  },
  plugins: [],
}
