import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0c0e12',
          900: '#12151c',
          800: '#1a1f2b',
          100: '#e8eaef',
        },
        accent: { DEFAULT: '#d4a82a', muted: '#8a7220' },
        border: '#2a3142',
      },
      borderColor: {
        DEFAULT: '#2a3142',
        border: '#2a3142',
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'Georgia', 'serif'],
      },
      keyframes: {
        'cta-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(212, 168, 42, 0.55)' },
          '50%': { boxShadow: '0 0 0 16px rgba(212, 168, 42, 0)' },
        },
      },
      animation: {
        'cta-pulse': 'cta-pulse 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
export default config
