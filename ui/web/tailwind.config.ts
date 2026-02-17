import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        terminal: {
          bg: '#0d0d0d',
          border: '#2a2a2a',
          cyan: '#22d3ee',
          green: '#4ade80',
          yellow: '#facc15',
          red: '#f87171',
          purple: '#a78bfa',
          gray: '#71717a',
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
