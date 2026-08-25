/**
 * ESLint 9 (flat config) для Mini App.
 *
 * Набор намеренно узкий: ловим реальные дефекты (необъявленные переменные,
 * забытые await, неверные хуки React), но НЕ навязываем форматирование —
 * существующий код не переформатируется.
 */

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  { ignores: ["dist/**", "app.html", "node_modules/**", "*.timestamp-*.mjs"] },
  js.configs.recommended,
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser, ...globals.es2021 },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Неиспользуемые переменные — предупреждение, а не ошибка:
      // в JSX-компонентах хватает намеренно распакованных пропсов.
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^[A-Z_]" }],
      "no-undef": "error",
    },
  },
];
