import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#0F1C27",
          secondary: "#9FAAB2",
          accent: "#FF5641",
          accentHover: "#FF735D",
          surface: "#132533",
          surfaceAlt: "#1B3343",
          border: "#244456",
          background: "#08121A"
        }
      },
      fontFamily: {
        dava: ["'Dava Sans'", "'Segoe UI'", "Helvetica", "Arial", "sans-serif"],
        sans: ["'Dava Sans'", "'Segoe UI'", "Helvetica", "Arial", "sans-serif"]
      },
      boxShadow: {
        card: "0 10px 30px -12px rgba(25, 43, 55, 0.25)"
      }
    }
  },
  plugins: []
};

export default config;
