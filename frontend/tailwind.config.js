/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f7f3ea", card: "#fffdf8", line: "#e3dccd", ink: "#1f2a1f", muted: "#5b6658",
        forest: { 50: "#eef5ef", 100: "#d7e8da", 600: "#2f6b3f", 700: "#1e4d2b", 800: "#163a20" },
        saffron: { 50: "#fff6e8", 100: "#fde7c4", 500: "#e08a1e", 600: "#b86e10", 700: "#8a520b" },
        alert: { 50: "#fdf0ec", 600: "#b4441f", 700: "#8f3517" },
      },
      fontFamily: {
        sans: ['"Noto Sans"', '"Noto Sans Devanagari"', '"Nirmala UI"', "system-ui", "sans-serif"],
        deva: ['"Noto Serif Devanagari"', '"Noto Sans Devanagari"', '"Nirmala UI"', "serif"],
      },
    },
  },
  plugins: [],
};
