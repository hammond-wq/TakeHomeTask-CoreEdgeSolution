/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
      },
      colors: {
        brand: { DEFAULT: "#64a12d", dark: "#4e7f22" }, // leaf green
        accent: "#42b883", // vite green
      },
    },
  },
  plugins: [],
};
