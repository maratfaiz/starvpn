import { useEffect, useState } from "react";
import * as api from "../data/mockApi.js";
import BottomSheet from "../components/BottomSheet.jsx";

const STRIP_ITEMS = [
  { key: "users_total", label: "Юзеров", color: "text-ink" },
  { key: "users_active_subs", label: "Активных", color: "text-success" },
  { key: "users_online", label: "Онлайн", color: "text-success" },
  { key: "referral_days_total", label: "Дней за рефералов", color: "text-gold" },
  { key: "payments_total", label: "Платежей", color: "text-ink" },
  { key: "users_banned", label: "Банов", color: "text-danger" },
];

const FILTERS = [
  { id: "all", label: "Все" },
  { id: "active", label: "Активные" },
  { id: "banned", label: "Забанены" },
];

const SUB_TABS = [
  { id: "users", label: "👥 Юзеры" },
  { id: "bc", label: "📢 Рассылка" },
  { id: "act", label: "⚡ Действия" },
];

function fmtUser(u) {
  return u.username ? `@${u.username}` : `ID ${u.tg_id}`;
}

export default function AdminScreen({ showToast }) {
  const [stats, setStats] = useState(null);
  const [subTab, setSubTab] = useState("users");

  // users
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersLoadingMore, setUsersLoadingMore] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [cursor, setCursor] = useState(0);
  const [total, setTotal] = useState(0);
  const [selectedUser, setSelectedUser] = useState(null);

  // broadcast
  const [broadcastText, setBroadcastText] = useState("");
  const [broadcastSending, setBroadcastSending] = useState(false);

  const loadStats = () => api.getAdminStats().then(setStats);

  const loadUsers = async (reset) => {
    if (reset) setUsersLoading(true);
    const { users: page, nextCursor, total: t } = await api.getAdminUsers({ search, cursor: reset ? 0 : cursor });
    setUsers(reset ? page : (prev) => [...prev, ...page]);
    setCursor(nextCursor ?? (reset ? page.length : cursor + page.length));
    setTotal(t);
    setUsersLoading(false);
    setUsersLoadingMore(false);
  };

  useEffect(() => {
    loadStats();
    loadUsers(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const t = setTimeout(() => loadUsers(true), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const filteredUsers = users.filter((u) => {
    if (filter === "active") return u.subscription_active;
    if (filter === "banned") return u.banned;
    return true;
  });

  const openUser = async (tgId) => {
    const u = await api.getAdminUser(tgId);
    setSelectedUser(u);
  };

  const refreshSelectedUser = async () => {
    if (!selectedUser) return;
    const u = await api.getAdminUser(selectedUser.tg_id);
    setSelectedUser(u);
    setUsers((prev) => prev.map((x) => (x.tg_id === u.tg_id ? u : x)));
  };

  const grantDays = async () => {
    await api.adminGrantDays(selectedUser.tg_id, 30);
    showToast("✅ Выдано 30 дней");
    refreshSelectedUser();
  };
  const banUser = async () => {
    await api.adminBanUser(selectedUser.tg_id);
    showToast("🚫 Пользователь забанен");
    refreshSelectedUser();
  };
  const unbanUser = async () => {
    await api.adminUnbanUser(selectedUser.tg_id);
    showToast("✅ Разбанен");
    refreshSelectedUser();
  };
  const messageUser = async () => {
    const text = window.prompt("Сообщение пользователю:");
    if (!text) return;
    try {
      await api.adminMessageUser(selectedUser.tg_id, text);
      showToast("✅ Сообщение отправлено");
    } catch (e) {
      showToast("❌ " + e.message);
    }
  };

  const sendBroadcast = async () => {
    setBroadcastSending(true);
    try {
      const res = await api.sendBroadcast(broadcastText);
      showToast(`✅ Отправлено ${res.sent_to} пользователям`);
      setBroadcastText("");
    } catch (e) {
      showToast("❌ " + e.message);
    } finally {
      setBroadcastSending(false);
    }
  };

  const exportCSV = () => {
    const csv = api.exportUsersCSV();
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "star_vpn_users.csv";
    a.click();
    URL.revokeObjectURL(url);
    showToast("📊 CSV выгружен");
  };

  const banById = async () => {
    const id = window.prompt("Telegram ID для бана:");
    if (!id) return;
    await api.adminBanUser(Number(id));
    showToast("🚫 Забанен ID " + id);
    loadUsers(true);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-2">
        {STRIP_ITEMS.map((s) => (
          <div key={s.key} className="bg-app-card border border-white/[.06] rounded-2xl py-3 text-center">
            <div className={`font-display font-extrabold text-[17px] ${s.color}`}>{stats ? stats[s.key] : "—"}</div>
            <div className="font-medium text-[10px] text-ink/40 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-1.5 overflow-x-auto">
        {SUB_TABS.map((t) => {
          const active = t.id === subTab;
          return (
            <button
              key={t.id}
              onClick={() => setSubTab(t.id)}
              className="relative px-3 py-2 rounded-xl font-display font-semibold text-xs whitespace-nowrap flex-shrink-0"
              style={{
                background: active ? "rgba(255,184,0,.12)" : "#12151C",
                border: `1px solid ${active ? "rgba(255,184,0,.4)" : "rgba(255,255,255,.06)"}`,
                color: active ? "#FFB800" : "rgba(245,243,238,.55)",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {subTab === "users" && (
        <div className="flex flex-col gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 Поиск по @username или ID"
            className="w-full bg-app-card border border-white/10 rounded-[13px] px-3.5 py-3 font-medium text-sm text-ink outline-none placeholder:text-ink/30"
          />
          <div className="flex gap-1.5 overflow-x-auto">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className="px-3 py-1.5 rounded-full font-display font-semibold text-[11px] whitespace-nowrap flex-shrink-0"
                style={{
                  background: filter === f.id ? "rgba(255,184,0,.12)" : "#12151C",
                  border: `1px solid ${filter === f.id ? "rgba(255,184,0,.4)" : "rgba(255,255,255,.06)"}`,
                  color: filter === f.id ? "#FFB800" : "rgba(245,243,238,.5)",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {usersLoading ? (
            <div className="text-center py-8 text-ink/40 text-sm">Загрузка…</div>
          ) : (
            <div className="flex flex-col gap-2">
              {filteredUsers.map((u) => (
                <button
                  key={u.tg_id}
                  onClick={() => openUser(u.tg_id)}
                  className="bg-app-card border border-white/[.06] rounded-2xl px-3.5 py-3 flex items-center gap-3 text-left"
                >
                  <div className="w-9 h-9 rounded-full bg-gold/10 flex items-center justify-center font-display font-bold text-xs text-gold flex-shrink-0">
                    {u.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-[13px] text-ink truncate">{u.name}</div>
                    <div className="font-medium text-[11px] text-ink/40">{fmtUser(u)}</div>
                  </div>
                  {u.banned && <span className="font-semibold text-[10px] text-danger bg-danger/10 px-2 py-0.5 rounded-md">БАН</span>}
                  {!u.banned && u.subscription_active && (
                    <span className="font-semibold text-[10px] text-success bg-success/10 px-2 py-0.5 rounded-md">Активен</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {cursor !== null && cursor < total && !usersLoading && (
            <button
              onClick={async () => {
                setUsersLoadingMore(true);
                await loadUsers(false);
              }}
              disabled={usersLoadingMore}
              className="mx-auto px-5 py-2 rounded-full border border-white/10 font-display font-semibold text-xs text-ink/60"
            >
              {usersLoadingMore ? "Загрузка…" : "Ещё"}
            </button>
          )}
        </div>
      )}

      {subTab === "bc" && (
        <div className="flex flex-col gap-2.5">
          <div className="font-semibold text-[13px] text-ink">📢 Рассылка пользователям</div>
          <textarea
            value={broadcastText}
            onChange={(e) => setBroadcastText(e.target.value)}
            rows={5}
            placeholder={"Текст сообщения (HTML поддерживается)\n\nПример:\n<b>Акция!</b> 7 дней бесплатно 🎉"}
            className="w-full resize-none bg-app-card border border-white/10 rounded-[13px] px-3.5 py-3 font-medium text-[13px] text-ink outline-none placeholder:text-ink/30 leading-relaxed"
          />
          <div className="font-semibold text-[10.5px] text-ink/40 uppercase tracking-wide">Предпросмотр</div>
          <div className="bg-app-card border border-white/[.06] rounded-2xl px-3.5 py-3 font-medium text-[13px] text-ink/70 min-h-[52px] whitespace-pre-wrap">
            {broadcastText.trim() ? broadcastText : "Начни вводить текст…"}
          </div>
          <div className="font-medium text-[11px] text-ink/40">Отправится всем незабаненным пользователям</div>
          <button
            onClick={sendBroadcast}
            disabled={broadcastSending || !broadcastText.trim()}
            className="w-full py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[13.5px] text-[#1A1408] disabled:opacity-50"
          >
            {broadcastSending ? "Отправляем…" : "Отправить рассылку"}
          </button>
        </div>
      )}

      {subTab === "act" && (
        <div className="grid grid-cols-2 gap-2.5">
          <button
            onClick={() => {
              loadStats();
              showToast("✅ Обновлено");
            }}
            className="bg-app-card border border-white/[.06] rounded-2xl py-4 px-3 text-center font-display font-semibold text-xs text-ink"
          >
            🔄<div className="mt-1.5">Обновить статистику</div>
          </button>
          <button onClick={() => setSubTab("bc")} className="bg-app-card border border-white/[.06] rounded-2xl py-4 px-3 text-center font-display font-semibold text-xs text-ink">
            📢<div className="mt-1.5">Сделать рассылку</div>
          </button>
          <button onClick={exportCSV} className="bg-app-card border border-white/[.06] rounded-2xl py-4 px-3 text-center font-display font-semibold text-xs text-ink">
            📊<div className="mt-1.5">Экспорт CSV</div>
          </button>
          <button onClick={() => setSubTab("users")} className="bg-app-card border border-white/[.06] rounded-2xl py-4 px-3 text-center font-display font-semibold text-xs text-ink">
            🔍<div className="mt-1.5">Найти юзера</div>
          </button>
          <button onClick={banById} className="bg-danger/[.08] border border-danger/30 rounded-2xl py-4 px-3 text-center font-display font-semibold text-xs text-danger">
            🚫<div className="mt-1.5">Бан по ID</div>
          </button>
        </div>
      )}

      <BottomSheet open={!!selectedUser} onClose={() => setSelectedUser(null)} title={selectedUser ? fmtUser(selectedUser) : ""} maxHeight="70%">
        {selectedUser && (
          <div className="flex flex-col gap-3">
            <div className="bg-app-card border border-white/[.06] rounded-2xl overflow-hidden">
              {[
                ["Имя", selectedUser.name],
                ["ID", selectedUser.tg_id],
                ["Подписка", selectedUser.subscription_active ? "Активна" : "Нет"],
                ["Истекает", selectedUser.expires_at || "—"],
                ["Дней от рефералов", selectedUser.extra_days_granted],
                ["Статус", selectedUser.banned ? "Забанен" : "Обычный"],
              ].map(([label, value], i, arr) => (
                <div key={label} className={`flex justify-between px-3.5 py-2.5 ${i < arr.length - 1 ? "border-b border-white/[.05]" : ""}`}>
                  <span className="font-medium text-[12.5px] text-ink/45">{label}</span>
                  <span className="font-semibold text-[12.5px] text-ink">{String(value)}</span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              <button onClick={grantDays} className="py-3 rounded-[14px] bg-gold/10 border border-gold/30 font-display font-semibold text-xs text-gold">
                Выдать 30 дней
              </button>
              <button onClick={messageUser} className="py-3 rounded-[14px] bg-white/[.05] border border-white/10 font-display font-semibold text-xs text-ink">
                Написать
              </button>
              {selectedUser.banned ? (
                <button onClick={unbanUser} className="col-span-2 py-3 rounded-[14px] bg-success/10 border border-success/30 font-display font-semibold text-xs text-success">
                  Разбанить
                </button>
              ) : (
                <button onClick={banUser} className="col-span-2 py-3 rounded-[14px] bg-danger/10 border border-danger/30 font-display font-semibold text-xs text-danger">
                  Забанить
                </button>
              )}
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  );
}
