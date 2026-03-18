import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'IBM Plex Mono'", "monospace"],
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'DM Sans'", "sans-serif"],
      },
      colors: {
        bg: {
          primary: "#0a0b0f",
          secondary: "#111318",
          card: "#13151c",
          elevated: "#1a1d27",
          border: "#252836",
        },
        accent: {
          cyan: "#00d4ff",
          "cyan-dim": "#00d4ff30",
          amber: "#ffb340",
          "amber-dim": "#ffb34030",
          red: "#ff4757",
          "red-dim": "#ff475720",
          green: "#00e676",
          "green-dim": "#00e67620",
          purple: "#b085ff",
          "purple-dim": "#b085ff20",
        },
        text: {
          primary: "#e8eaf0",
          secondary: "#8b91a8",
          muted: "#4a5068",
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.35s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
