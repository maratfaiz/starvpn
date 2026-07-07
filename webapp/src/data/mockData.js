// Mock data for the STAR VPN Mini App UI.
// No backend calls yet — this feeds the fully interactive frontend
// until the real API (bot/api.py) is wired in.

export const subscription = {
  planName: "Premium",
  daysLeft: 23,
  totalDays: 30,
  expiryDate: "4 августа 2026",
  connectionLabel: "Подключено",
};

export const server = {
  flag: "🇳🇱",
  name: "Амстердам #2",
  ping: 34,
  protocol: "VLESS Reality",
};

export const speedValue = "184";
export const trafficUsedTotal = "64.2";
export const trafficBars = [22, 38, 30, 55, 41, 68, 47];

export const starsBalanceInitial = 340;

export const devicesInitial = [
  {
    id: 1,
    name: "iPhone 15 Pro",
    type: "phone",
    current: true,
    lastActive: "Сейчас",
    traffic: "18.4",
    connectedSince: "12 марта 2026",
    location: "Москва, Россия",
    ip: "10.66.12.4",
    protocol: "WireGuard",
  },
  {
    id: 2,
    name: "MacBook Air",
    type: "laptop",
    current: false,
    lastActive: "2 ч назад",
    traffic: "31.7",
    connectedSince: "2 июня 2026",
    location: "Москва, Россия",
    ip: "10.66.12.9",
    protocol: "WireGuard",
  },
  {
    id: 3,
    name: "iPad mini",
    type: "tablet",
    current: false,
    lastActive: "Вчера",
    traffic: "14.1",
    connectedSince: "28 мая 2026",
    location: "Санкт-Петербург, Россия",
    ip: "10.66.12.21",
    protocol: "OpenVPN",
  },
];

export const devicesLimit = 5;

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

export const renewPlans = [
  { id: 1, label: "1 месяц", days: 30, perMonth: "199 ⭐ / мес", price: 199, popular: false },
  { id: 2, label: "3 месяца", days: 90, perMonth: "183 ⭐ / мес", price: 549, popular: true },
  { id: 3, label: "12 месяцев", days: 365, perMonth: "166 ⭐ / мес", price: 1990, popular: false },
];

export const giftDayOptions = [7, 30, 90, 180];

export const topupPacks = [
  { id: 1, stars: 100, priceLabel: "149 ₽", best: false },
  { id: 2, stars: 500, priceLabel: "699 ₽", best: true },
  { id: 3, stars: 1000, priceLabel: "1290 ₽", best: false },
  { id: 4, stars: 2500, priceLabel: "2990 ₽", best: false },
];
