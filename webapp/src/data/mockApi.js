// Mock API layer — simulates bot/api.py responses so the UI can be built
// and exercised without a running backend. Every function mirrors a real
// endpoint (see comments) and returns after a short delay so loading
// states behave like the real thing. Swap the function bodies for real
// `fetch` calls once the backend is wired up; call sites shouldn't need
// to change.

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));

// Sole "am I the admin" switch for this mock build. The real endpoint is
// GET /api/admin/check, gated server-side by TELEGRAM_ADMIN_ID.
const MOCK_IS_ADMIN = true;

let seq = 100;
const nextId = () => ++seq;

const store = {
  me: {
    subscription_active: true,
    plan_name: "Premium",
    days_left: 23,
    total_days: 30,
    expires_at: "2026-08-04",
    trial_used: false,
    device_count: 2,
    max_devices: 3,
    server_flag: "🇳🇱",
    server_country: "Нидерланды",
    server_city: "Амстердам",
    server_protocol: "VLESS + Reality",
    server_tls: "TLS 1.3",
    server_host: "vpn.starvpn.ru",
    server_sni: "www.google.com",
    server_port: 443,
  },
  devices: [
    {
      id: 1,
      name: "iPhone 15 Pro",
      type: "ios",
      traffic_gb: 18.42,
      last_online: "Сейчас",
      status_label: "Онлайн",
      slot: 1,
      created_at: "2026-03-12",
      link: "vless://a1b2c3@vpn.starvpn.ru:443?type=tcp&security=reality&sni=www.google.com#STAR-VPN-iPhone-15-Pro",
      sub_url: "https://starvpnservice.ru/sub/ios_tg_a1b2c3",
    },
    {
      id: 2,
      name: "MacBook Air",
      type: "macos",
      traffic_gb: 31.7,
      last_online: "2 ч назад",
      status_label: "Не в сети",
      slot: 2,
      created_at: "2026-06-02",
      link: "vless://d4e5f6@vpn.starvpn.ru:443?type=tcp&security=reality&sni=www.google.com#STAR-VPN-MacBook-Air",
      sub_url: "https://starvpnservice.ru/sub/macos_tg_d4e5f6",
    },
  ],
  plans: [
    { key: "plan_1m", label: "1 месяц", days: 30, stars: 199, discount: 0 },
    { key: "plan_3m", label: "3 месяца", days: 90, stars: 549, discount: 8 },
    { key: "plan_12m", label: "12 месяцев", days: 365, stars: 1990, discount: 17 },
  ],
  cryptoPlans: [
    { key: "plan_1m", usd: 2.1 },
    { key: "plan_3m", usd: 5.7 },
    { key: "plan_12m", usd: 20.5 },
  ],
  adminStats: {
    users_total: 1284,
    users_active_subs: 341,
    users_online: 58,
    referral_days_total: 960,
    payments_total: 902,
    users_banned: 6,
  },
  adminUsers: Array.from({ length: 34 }, (_, i) => ({
    tg_id: 100000 + i,
    name: `Пользователь ${i + 1}`,
    username: i % 3 === 0 ? null : `user${i + 1}`,
    subscription_active: i % 2 === 0,
    expires_at: i % 2 === 0 ? "2026-08-04" : null,
    extra_days_granted: (i * 7) % 90,
    banned: i % 11 === 0,
    joined_at: "2026-0" + ((i % 6) + 1) + "-1" + (i % 9),
  })),
  pendingGift: {
    id: 501,
    from_name: "Артём К.",
    plan_label: "3 месяца",
    days: 90,
  },
};

function genVlessLink(type, deviceId) {
  const rand = Math.random().toString(16).slice(2, 8);
  return `vless://${rand}@vpn.starvpn.ru:443?type=tcp&security=reality&sni=www.google.com#STAR-VPN-${type}-${deviceId}`;
}

function genSubUrl(type, deviceId) {
  return `https://starvpnservice.ru/sub/${type}_tg_${deviceId}`;
}

// ─── GET /api/me, /api/devices ───
export async function getMe() {
  await delay();
  return { ...store.me };
}

export async function getDevices() {
  await delay();
  return store.devices.map((d) => ({ ...d }));
}

// ─── POST /api/devices, GET /api/devices/:id/link, DELETE /api/devices/:id ───
export async function addDevice(type, label) {
  await delay(500);
  const id = nextId();
  const device = {
    id,
    name: label,
    type,
    traffic_gb: 0,
    last_online: "Никогда",
    status_label: "Не в сети",
    slot: store.devices.length + 1,
    created_at: new Date().toISOString().slice(0, 10),
    link: genVlessLink(type, id),
    sub_url: genSubUrl(type, id),
  };
  store.devices.push(device);
  store.me.device_count += 1;
  return { ...device };
}

export async function getDeviceLink(id) {
  await delay();
  const d = store.devices.find((x) => x.id === id);
  if (!d) throw new Error("Устройство не найдено");
  return { link: d.link, sub_url: d.sub_url };
}

export async function deleteDevice(id) {
  await delay(400);
  store.devices = store.devices.filter((d) => d.id !== id);
  store.me.device_count = Math.max(0, store.me.device_count - 1);
  return { success: true };
}

// ─── POST /api/trial ───
export async function activateTrial() {
  await delay(500);
  store.me.subscription_active = true;
  store.me.trial_used = true;
  store.me.plan_name = "Trial";
  store.me.days_left = 2;
  store.me.total_days = 2;
  return { ...store.me };
}

// ─── GET /api/referral ───
// ─── GET /api/plans, /api/crypto-plans ───
export async function getPlans() {
  await delay();
  return store.plans.map((p) => ({ ...p }));
}

export async function getCryptoPlans() {
  await delay();
  return store.cryptoPlans.map((p) => ({ ...p }));
}

// ─── POST /api/invoice/renew, /api/invoice/crypto ───
export async function invoiceRenew(planKey) {
  await delay(600);
  const plan = store.plans.find((p) => p.key === planKey);
  if (!plan) throw new Error("Тариф не найден");
  store.me.subscription_active = true;
  store.me.days_left += plan.days;
  return { success: true, days: plan.days };
}

// ─── POST /api/invoice/gift ───
export async function invoiceGift(payload) {
  await delay(600);
  if (!payload.recipient) throw new Error("Укажи получателя");
  return { success: true };
}

// ─── GET /api/gift/pending, POST /api/gift/:id/accept ───
export async function checkGiftNotification() {
  await delay(300);
  return store.pendingGift ? { ...store.pendingGift } : null;
}

export async function acceptGift(id) {
  await delay(400);
  if (store.pendingGift?.id === id) {
    store.me.days_left += store.pendingGift.days;
    store.pendingGift = null;
  }
  return { success: true };
}

// ─── GET /api/admin/check ───
export async function adminCheck() {
  await delay(150);
  return { is_admin: MOCK_IS_ADMIN };
}

export async function getAdminStats() {
  await delay();
  return { ...store.adminStats };
}

export async function getAdminUsers({ search = "", cursor = 0, limit = 12 } = {}) {
  await delay(300);
  const filtered = search
    ? store.adminUsers.filter(
        (u) =>
          String(u.tg_id).includes(search) ||
          u.name.toLowerCase().includes(search.toLowerCase()) ||
          (u.username && u.username.toLowerCase().includes(search.toLowerCase()))
      )
    : store.adminUsers;
  const page = filtered.slice(cursor, cursor + limit);
  return { users: page, nextCursor: cursor + limit < filtered.length ? cursor + limit : null, total: filtered.length };
}

export async function getAdminUser(tgId) {
  await delay();
  const u = store.adminUsers.find((x) => x.tg_id === tgId);
  if (!u) throw new Error("Пользователь не найден");
  return { ...u };
}

export async function adminGrantDays(tgId, _days) {
  await delay(400);
  const u = store.adminUsers.find((x) => x.tg_id === tgId);
  if (u) u.subscription_active = true;
  return { success: true };
}

export async function adminBanUser(tgId) {
  await delay(300);
  const u = store.adminUsers.find((x) => x.tg_id === tgId);
  if (u) u.banned = true;
  return { success: true };
}

export async function adminUnbanUser(tgId) {
  await delay(300);
  const u = store.adminUsers.find((x) => x.tg_id === tgId);
  if (u) u.banned = false;
  return { success: true };
}

export async function adminMessageUser(tgId, text) {
  await delay(400);
  if (!text.trim()) throw new Error("Пустое сообщение");
  return { success: true };
}

export async function sendBroadcast(text) {
  await delay(700);
  if (!text.trim()) throw new Error("Пустой текст рассылки");
  return { success: true, sent_to: store.adminUsers.length };
}

export function exportUsersCSV() {
  const header = "tg_id,name,username,subscription_active,expires_at,extra_days_granted,banned,joined_at";
  const rows = store.adminUsers.map((u) =>
    [u.tg_id, u.name, u.username || "", u.subscription_active, u.expires_at || "", u.extra_days_granted, u.banned, u.joined_at].join(",")
  );
  return [header, ...rows].join("\n");
}
