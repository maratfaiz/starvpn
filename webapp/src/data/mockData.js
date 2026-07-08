// Mock data for the STAR VPN Mini App UI.
// No backend calls yet — this feeds the fully interactive frontend
// until the real API (bot/api.py) is wired in.

export const server = {
  flag: "🇳🇱",
  name: "Амстердам #2",
  ping: 34,
  protocol: "VLESS Reality",
};

export const speedValue = "184";

export const referral = {
  code: "STAR-9X4K2",
  bonusDays: 30,
  invitedCount: 6,
  daysEarned: 44,
  starsEarned: 100,
};

export const rewardTiers = [
  { id: 1, count: "1", label: "Друг оформил подписку", reward: "+7 дней" },
  { id: 2, count: "5", label: "Бонус за 5 друзей", reward: "+30 дней" },
  { id: 3, count: "10", label: "Бонус за 10 друзей", reward: "100 ⭐" },
];

export const daysHistoryInitial = [
  { id: 1, label: "Реферал: Артём К.", date: "3 дня назад", days: 7, type: "referral" },
  { id: 2, label: "Реферал: Мария С.", date: "неделю назад", days: 7, type: "referral" },
  { id: 3, label: "Бонус за 5 друзей", date: "2 недели назад", days: 30, type: "bonus" },
  { id: 4, label: "Продление подписки", date: "месяц назад", days: 30, type: "purchase" },
];

export const account = {
  initials: "МК",
  name: "Марат К.",
  username: "@helloimmarat",
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
  { id: 1, label: "1 месяц", days: 30, perMonth: "99 ⭐ / мес", price: 99, rub: 199, popular: false },
  { id: 2, label: "3 месяца", days: 90, perMonth: "83 ⭐ / мес", price: 249, rub: 499, popular: true },
  { id: 3, label: "6 месяцев", days: 180, perMonth: "75 ⭐ / мес", price: 449, rub: 899, popular: false },
];

export const giftDayOptions = [7, 30, 90, 180];
