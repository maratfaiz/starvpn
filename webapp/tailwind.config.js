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
      },
      backdropBlur: {
        glass: "12px",
      },
    },
  },
  plugins: [],
};
