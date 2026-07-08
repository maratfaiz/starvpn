/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Map to Telegram CSS variables injected by WebApp
        tg: {
          bg: "var(--tg-theme-bg-color)",
          text: "var(--tg-theme-text-color)",
          hint: "var(--tg-theme-hint-color)",
          link: "var(--tg-theme-link-color)",
          button: "var(--tg-theme-button-color)",
          buttonText: "var(--tg-theme-button-text-color)",
          secondaryBg: "var(--tg-theme-secondary-bg-color)",
        },
        // STAR VPN dark/gold design system
        app: {
          bg: "#05070A",
          card: "#12151C",
          sheet: "#0E1116",
        },
        gold: {
          DEFAULT: "#F7CE68",
          dark: "#C9962F",
        },
        ink: "#F5F3EE",
        success: "#2ED9A6",
        danger: "#E2554F",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "system-ui", "sans-serif"],
      },
      backdropBlur: {
        glass: "12px",
      },
      boxShadow: {
        sheet: "0 -20px 50px rgba(0,0,0,.5)",
      },
    },
  },
  plugins: [],
};
