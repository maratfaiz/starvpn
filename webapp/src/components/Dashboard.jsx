/**
 * Main dashboard screen.
 * Shows: user greeting, subscription status, action buttons.
 * Glassmorphism style + Telegram theme sync.
 */

import { useEffect, useState } from "react";
import Payment from "./Payment.jsx";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function Dashboard({ user }) {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("home"); // "home" | "payment"

  useEffect(() => {
    if (!user) { setLoading(false); return; }

    axios
      .get(`${API_BASE}/api/subscription`, {
        headers: { "X-Init-Data": window.Telegram?.WebApp?.initData || "" },
      })
      .then((res) => setSubscription(res.data))
      .catch(() => setSubscription(null))
      .finally(() => setLoading(false));
  }, [user]);

  const haptic = (type = "impact") => {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(type);
  };

  if (view === "payment") {
    return <Payment onBack={() => { haptic("light"); setView("home"); }} />;
  }

  return (
    <div className="flex flex-col gap-4 p-4 max-w-md mx-auto">
      {/* Header */}
      <div className="glass-card p-5 text-center">
        <h1 className="text-2xl font-bold tracking-wide">⭐ STAR VPN</h1>
        <p className="text-tg-hint text-sm mt-1">
          {user ? `Привет, ${user.first_name}!` : "Добро пожаловать"}
        </p>
      </div>

      {/* Subscription status */}
      <div className="glass-card p-5">
        <h2 className="text-sm font-semibold text-tg-hint uppercase tracking-widest mb-3">
          Статус подписки
        </h2>
        {loading ? (
          <p className="text-tg-hint animate-pulse">Загрузка...</p>
        ) : subscription?.active ? (
          <>
            <p className="text-green-400 font-semibold text-lg">✅ Активна</p>
            <p className="text-tg-hint text-sm mt-1">
              Истекает: {new Date(subscription.expires_at).toLocaleDateString("ru-RU")}
            </p>
            <p className="text-tg-hint text-sm">
              Трафик: {subscription.used_traffic ?? "∞"} / {subscription.data_limit ?? "∞"}
            </p>
          </>
        ) : (
          <p className="text-red-400 font-semibold">❌ Нет активной подписки</p>
        )}
      </div>

      {/* VPN Config (shown when active) */}
      {subscription?.active && subscription?.config_link && (
        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-tg-hint uppercase tracking-widest mb-3">
            Конфигурация VPN
          </h2>
          <button
            className="w-full py-2 rounded-xl bg-tg-button text-tg-buttonText font-medium"
            onClick={() => {
              haptic("medium");
              navigator.clipboard.writeText(subscription.config_link);
              window.Telegram?.WebApp?.showAlert("Ссылка скопирована!");
            }}
          >
            📋 Скопировать config-ссылку
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-3">
        <button
          className="glass-card py-4 text-center font-semibold text-tg-button w-full"
          onClick={() => { haptic("medium"); setView("payment"); }}
        >
          💳 Купить / продлить подписку
        </button>

        <button
          className="glass-card py-4 text-center font-semibold text-tg-hint w-full"
          onClick={() => {
            haptic("light");
            const botUsername = import.meta.env.VITE_BOT_USERNAME || "star_vpn_bot";
            const refLink = `https://t.me/${botUsername}?start=${user?.id}`;
            navigator.clipboard.writeText(refLink);
            window.Telegram?.WebApp?.showAlert("Реферальная ссылка скопирована!");
          }}
        >
          👥 Пригласить друга (+30 дней за 2 чел.)
        </button>
      </div>
    </div>
  );
}
