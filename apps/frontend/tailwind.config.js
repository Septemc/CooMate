/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        main: 'var(--bg-main)',
        sidebar: 'var(--bg-sidebar)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        border: 'var(--border-color)',
        card: {
          DEFAULT: 'var(--card-bg)',
          hover: 'var(--card-hover)',
        },
        brand: {
          DEFAULT: 'var(--brand-primary)',
          hover: 'var(--brand-hover)',
        },
        input: 'var(--input-bg)',
        msg: {
          user: 'var(--msg-user)',
          ai: 'var(--msg-ai)',
        },
        'btn-text': 'var(--btn-text)',
        step: {
          1: '#3b82f6',  // blue - 反问成立性
          2: '#22c55e',  // green - 深挖追问
          3: '#eab308',  // yellow - 复盘情绪
          4: '#a855f7',  // purple - 多角度
          5: '#f97316',  // orange - 微型实验
        }
      }
    },
  },
  plugins: [],
}
