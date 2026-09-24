// Real API layer for the STAR VPN Mini App — talks to bot/api.py.
//
// Same function names/signatures as the old mockApi.js so screens didn't
// need to change; only the bodies now hit the real backend. Auth is the
// Telegram Mini App's initData string, sent as X-Telegram-Init-Data (the
// same header bot/api.py's _resolve_tg_id/_tg_id expect).
//
// The Mini App is served by the same FastAPI app as the API, so relative
// paths work in production; VITE_API_BASE only matters for `npm run dev`
// against a non-local backend.

const API_BASE = import.meta.env.VITE_API_BASE || "";

function initData() {
  return window.Telegram?.WebApp?.initData || "";
}

async function apiFetch(path, { method = "GET", body } = {}) {
  const headers = {};
  const raw = initData();
  if (raw) headers["X-Telegram-Init-Data"] = raw;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    throw new Error((data && data.detail) || res.statusText || `HTTP ${res.status}`);
  }
  return data;
}

// ─── Telegram payment helpers ───

// Stars invoices resolve synchronously inside the Telegram client via
// openInvoice; outside Telegram (e.g. `npm run dev`) we just open the link.
export function openTelegramInvoice(url) {
  return new Promise((resolve) => {
    const tg = window.Telegram?.WebApp;
    if (tg?.openInvoice) {
      tg.openInvoice(url, (status) => resolve(status));
    } else {
      window.open(url, "_blank");
      resolve("pending");
    }
  });
}

// Card/crypto go to a hosted checkout page (Robokassa/@CryptoBot) — no
// synchronous result, confirmation arrives later via webhook.
export function openExternalPayment(url) {
  const tg = window.Telegram?.WebApp;
  if (tg?.openLink) tg.openLink(url);
  else window.open(url, "_blank");
}

// ─── Devices ───
// GET /api/devices returns `name` as the platform-type key (ios/android/…),
// not a display name — the display name is `custom_name` (nullable). See
// CLAUDE.md "Device names". We remap to {type, name: <display>} so screens
// keep working with a `name` that's actually meant to be shown.

const DEVICE_LABELS = {
  ios: "iPhone / iPad",
  android: "Android",
  macos: "macOS",
  windows: "Windows",
  linux: "Linux",
  androidtv: "Android TV",
  appletv: "Apple TV",
};

function mapDevice(d) {
  const type = d.type || d.name;
  return {
    id: d.id,
    slot: d.slot,
    type,
    name: d.custom_name || DEVICE_LABELS[type] || type,
    custom_name: d.custom_name || null,
    traffic_gb: d.traffic_gb || 0,
    online: !!d.online,
    last_online: d.last_online || "никогда",
    status_label: d.status_label || "неизвестно",
    created_at: d.created_at,
  };
}

export async function getMe() {
  return apiFetch("/api/me");
}

export async function getDevices() {
  const devices = await apiFetch("/api/devices");
  return devices.map(mapDevice);
}

export async function addDevice(type, label) {
  const d = await apiFetch("/api/devices", { method: "POST", body: { type, name: label } });
  return mapDevice(d);
}

export async function getDeviceLink(id) {
  return apiFetch(`/api/devices/${id}/link`);
}

export async function deleteDevice(id) {
  await apiFetch(`/api/devices/${id}`, { method: "DELETE" });
  return { success: true };
}

// ─── Trial ───

export async function activateTrial() {
  await apiFetch("/api/trial", { method: "POST" });
  return getMe();
}

// ─── Referral ───

export async function getReferral() {
  const r = await apiFetch("/api/referral");
  return {
    link: r.link,
    code: (r.link.split("start=")[1] || "").toUpperCase(),
    bonusDays: r.days_bonus,
    milestoneSize: r.milestone_size,
    paidCount: r.referral_count,
    daysEarned: r.extra_days_granted,
    achievements: r.achievements.map((a) => ({
      key: a.key,
      icon: a.icon,
      title: a.title,
      threshold: a.threshold,
      bonusDays: a.bonus_days,
      unlocked: a.unlocked,
    })),
  };
}

// ─── Renew (buy/extend subscription): Stars + card ───
// Crypto exists on the backend too (/api/crypto/plans, /api/invoice/crypto)
// but RenewSheet's UI only ever offered a Stars/card toggle — left as-is,
// adding a third payment method is a UI change beyond swapping mocks for
// real calls.

export async function getRenewPlans() {
  const [stars, card] = await Promise.all([apiFetch("/api/plans"), apiFetch("/api/card/plans")]);
  const rubByKey = Object.fromEntries(card.map((p) => [p.key, p.rub]));
  return stars.map((p) => ({
    id: p.key,
    label: p.label,
    days: p.days,
    price: p.stars,
    rub: rubByKey[p.key] ?? null,
    perMonth: `${Math.round(p.stars / (p.days / 30))} ⭐ / мес`,
    popular: p.key === "plan_3m",
  }));
}

export async function createRenewInvoice({ planKey, method, days }) {
  if (method === "stars") {
    return apiFetch("/api/invoice/renew", { method: "POST", body: { plan: planKey } });
  }
  const body = planKey ? { plan: planKey } : { days };
  return apiFetch("/api/invoice/card", { method: "POST", body });
}

// ─── Gift (Stars only from the Mini App — card/link gifting lives on the website) ───

export async function createGiftInvoice({ planKey, recipient, message }) {
  return apiFetch("/api/invoice/gift", {
    method: "POST",
    body: { plan: planKey, recipient, message: message || "" },
  });
}

export async function checkGiftNotification() {
  const { gift } = await apiFetch("/api/gift/pending");
  if (!gift) return null;
  return { id: gift.id, from_name: gift.sender_name, plan_label: gift.plan_label, days: gift.plan_days };
}

// Days are already granted (via the payment webhook) by the time this
// notification shows — this only marks it as read.
export async function acceptGift(id) {
  await apiFetch("/api/gift/seen", { method: "POST", body: { id } });
  return { success: true };
}

// ─── Admin ───

export async function adminCheck() {
  return apiFetch("/api/admin/check");
}

export async function getAdminStats() {
  const s = await apiFetch("/api/admin/stats");
  return {
    users_total: s.total_users,
    users_active_subs: s.active_subscriptions,
    users_online: s.online_now,
    referral_days_total: s.referral_days_total,
    payments_total: s.total_payments,
    users_banned: s.banned,
  };
}

function mapAdminUser(u) {
  return {
    tg_id: u.telegram_id,
    name: u.full_name || (u.username ? `@${u.username}` : `ID ${u.telegram_id}`),
    username: u.username || null,
    subscription_active: u.subscription_active,
    expires_at: u.subscription_expires_at,
    extra_days_granted: u.extra_days_granted,
    banned: u.is_banned,
    joined_at: u.created_at,
  };
}

export async function getAdminUsers({ search = "", cursor = 0, limit = 12 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(cursor) });
  if (search) params.set("q", search);
  const { users, total } = await apiFetch(`/api/admin/users?${params}`);
  const mapped = users.map(mapAdminUser);
  const nextCursor = cursor + mapped.length < total ? cursor + mapped.length : null;
  return { users: mapped, nextCursor, total };
}

export async function getAdminUser(tgId) {
  return mapAdminUser(await apiFetch(`/api/admin/user?q=${encodeURIComponent(tgId)}`));
}

export async function adminGrantDays(tgId, days) {
  return apiFetch("/api/admin/grant", { method: "POST", body: { telegram_id: tgId, days } });
}

export async function adminBanUser(tgId) {
  return apiFetch("/api/admin/ban", { method: "POST", body: { telegram_id: tgId } });
}

export async function adminUnbanUser(tgId) {
  return apiFetch("/api/admin/unban", { method: "POST", body: { telegram_id: tgId } });
}

export async function adminMessageUser(tgId, text) {
  return apiFetch("/api/admin/message", { method: "POST", body: { telegram_id: tgId, text } });
}

export async function sendBroadcast(text) {
  const r = await apiFetch("/api/admin/broadcast", { method: "POST", body: { text } });
  return { success: true, sent_to: r.sent };
}

// No bulk-export endpoint exists — page through /api/admin/users ourselves.
export async function exportUsersCSV() {
  const limit = 200;
  let offset = 0;
  let all = [];
  for (let i = 0; i < 25; i++) {
    const { users, total } = await getAdminUsers({ cursor: offset, limit });
    all = all.concat(users);
    offset += users.length;
    if (!users.length || offset >= total) break;
  }
  const header = "tg_id,name,username,subscription_active,expires_at,extra_days_granted,banned,joined_at";
  const rows = all.map((u) =>
    [u.tg_id, u.name, u.username || "", u.subscription_active, u.expires_at || "", u.extra_days_granted, u.banned, u.joined_at || ""].join(",")
  );
  return [header, ...rows].join("\n");
}
