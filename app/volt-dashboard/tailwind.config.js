/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive) / <alpha-value>)",
          foreground: "hsl(var(--destructive-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // ---- Volt console palette (design.md §3) ----
        'bg-0': '#0B0908',
        'bg-1': '#141110',
        'bg-2': '#1C1815',
        'bg-3': '#262019',
        line: '#2C251D',
        'line-strong': '#3D332A',
        'ink-1': '#EFE6D6',
        'ink-2': '#B3A58D',
        'ink-3': '#7D7160',
        'ink-4': '#57493A',
        amber: '#E8A33D',
        'amber-hi': '#F5C15C',
        copper: '#B87333',
        rust: '#A85B32',
        sand: '#C9A45C',
        stone: '#6E6353',
        vermilion: '#D95B33',
        dim: '#57493A',
      },
      fontFamily: {
        display: ['"Archivo Black"', 'Archivo', 'sans-serif'],
        sans: ['Archivo', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xs: "calc(var(--radius) - 6px)",
      },
      boxShadow: {
        panel: '0 0 0 1px #2C251D, 0 24px 48px -24px rgba(11,9,8,0.9)',
        glow: '0 0 12px rgba(232,163,61,0.25)',
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
      },
      maxWidth: {
        console: '1560px',
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        "caret-blink": {
          "0%,70%,100%": { opacity: "1" },
          "20%,50%": { opacity: "0" },
        },
        "rec-breathe": {
          "0%,100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        "ring-pulse": {
          "0%,100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
        "row-flash": {
          "0%, 100%": { backgroundColor: "transparent" },
          "16.6%": { backgroundColor: "#262019" },
          "33.3%": { backgroundColor: "transparent" },
          "50%": { backgroundColor: "#262019" },
          "66.6%": { backgroundColor: "transparent" },
          "83.3%": { backgroundColor: "#262019" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "caret-blink": "caret-blink 1.25s ease-out infinite",
        "rec-breathe": "rec-breathe 1.6s ease-in-out infinite",
        "ring-pulse": "ring-pulse 2.4s ease-in-out infinite",
        "row-flash": "row-flash 0.9s ease-in-out 1",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
