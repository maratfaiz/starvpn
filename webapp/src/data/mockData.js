// Mock data for the STAR VPN Mini App UI.
// No backend calls yet — this feeds the fully interactive frontend
// until the real API (bot/api.py) is wired in.

// Reward mechanic: flat days per paid+vested referral (no "every N"
// batching), a 30-day vesting hold before credit (refund/chargeback
// protection), and a monthly cap. Kept intentionally simple — no
// achievements/levels/leaderboards.
//
// monthlyCapDays/monthlyCapReferrals (90 days = 6 referrals, rolling
// 30-day window) mirrors bot/handlers/payment.py's REFERRAL_MONTHLY_CAP_DAYS
// — changed 2026-08-31 from an initial 365-days/365-day-window cap to match
// this screen's simplified copy (explicit product decision, see
// Agents_history.md).
export const referral = {
  code: "STAR-9X4K2",
  daysPerReferral: 15,
  vestingDays: 30,
  monthlyCapDays: 90,
  monthlyCapReferrals: 6,
  invitedCount: 6,
  daysEarned: 85,
};

export const daysHistoryInitial = [
  { id: 1, label: "Реферальный бонус", date: "3 дня назад", days: 15, type: "bonus" },
  { id: 2, label: "Реферальный бонус", date: "2 недели назад", days: 15, type: "bonus" },
  { id: 3, label: "Продление подписки", date: "месяц назад", days: 30, type: "purchase" },
];

export const account = {
  initials: "МК",
  name: "Марат К.",
  username: "@helloimmarat",
  appVersion: "1.2.0",
  siteUrl: "https://starvpnservice.ru",
  privacyUrl: "https://starvpnservice.ru/privacy.html",
  termsUrl: "https://starvpnservice.ru/terms.html",
};

export const settingsRows = [
  { id: "notifications", label: "Уведомления", detail: "", icon: "bell" },
  { id: "language", label: "Язык", detail: "Русский", icon: "globe" },
  { id: "privacy", label: "Конфиденциальность", detail: "", icon: "shield" },
  { id: "support", label: "Поддержка", detail: "", icon: "help" },
  { id: "about", label: "О приложении", detail: account.appVersion, icon: "info" },
];

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

// price — Stars price, rub — card price via Robokassa. Matches bot/handlers/payment.py PLANS.
export const renewPlans = [
  { id: 1, label: "1 месяц", days: 30, perMonth: "99 звёзд / мес", price: 99, rub: 199, popular: false },
  { id: 2, label: "3 месяца", days: 90, perMonth: "83 звезды / мес", price: 249, rub: 499, popular: true },
  { id: 3, label: "6 месяцев", days: 180, perMonth: "75 звёзд / мес", price: 449, rub: 899, popular: false },
];

export const giftDayOptions = [7, 30, 90, 180];
