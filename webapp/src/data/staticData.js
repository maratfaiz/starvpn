// Static, non-backend config for the STAR VPN Mini App UI — app version,
// legal/support links, and purely client-side preference rows that have no
// server counterpart. Anything that used to live here as *fake backend
// data* (server info, referral stats, plans, days history) now comes from
// ./api.js instead.

export const account = {
  appVersion: "1.2.0",
  siteUrl: "https://starvpnservice.ru",
  privacyUrl: "https://starvpnservice.ru/privacy.html",
  termsUrl: "https://starvpnservice.ru/terms.html",
  supportUrl: "https://t.me/hashprojects",
};

export const settingsRows = [
  { id: "notifications", label: "Уведомления", detail: "", icon: "bell" },
  { id: "language", label: "Язык", detail: "Русский", icon: "globe" },
  { id: "privacy", label: "Конфиденциальность", detail: "", icon: "shield" },
  { id: "support", label: "Поддержка", detail: "", icon: "help" },
  { id: "about", label: "О приложении", detail: account.appVersion, icon: "info" },
];

// Purely client-side preferences — nothing persists them server-side yet,
// same as the equivalent controls on the website (see CLAUDE.md history).
export const notificationTogglesInitial = [
  { id: "expiry", label: "Истечение подписки", on: true },
  { id: "devices", label: "Новые устройства", on: true },
  { id: "promo", label: "Акции и бонусы", on: false },
];

export const languageOptions = [
  { id: "ru", label: "Русский" },
  { id: "en", label: "English" },
  { id: "ua", label: "Українська" },
];

// Matches the Stars gift plan keys bot/api.py's _PLANS_API actually has
// (30/90/180 days) — a gift can't be for an arbitrary number of days, so
// this dropped the mock's "7" option. See GIFT_PLAN_BY_DAYS in App.jsx for
// the days → plan key mapping used when creating the invoice.
export const giftDayOptions = [30, 90, 180];
