import { StarIcon, GearIcon, SettingIcon, ChevronIcon, CrownIcon, CalendarIcon, CardIcon, HeadsetIcon } from "../components/icons.jsx";
import { planLabel } from "../utils/plan.js";

function openExternal(url) {
  const tg = window.Telegram?.WebApp;
  if (tg?.openLink) tg.openLink(url);
  else window.open(url, "_blank");
}

const GlobeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFB800" strokeWidth="2" strokeLinecap="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="2" y1="12" x2="22" y2="12" />
    <path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" />
  </svg>
);
const LockIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFB800" strokeWidth="2" strokeLinecap="round">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0110 0v4" />
  </svg>
);
const DocIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFB800" strokeWidth="2" strokeLinecap="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);
const RefreshIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polyline points="23 4 23 10 17 10" />
    <polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
  </svg>
);

const INFO_ROWS = [
  { icon: <GlobeIcon />, label: "Сайт", urlKey: "siteUrl" },
  { icon: <LockIcon />, label: "Политика конфиденциальности", urlKey: "privacyUrl" },
  { icon: <DocIcon />, label: "Условия использования", urlKey: "termsUrl" },
];

export default function AccountScreen({
  account,
  subscription,
  settingsRows,
  onOpenSetting,
  onManageSubscription,
  onLogout,
  onOpenInstructions,
  onRefresh,
  refreshing,
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="relative flex items-center gap-3.5 px-0.5 py-1.5 overflow-hidden">
        <div
          className="absolute top-1/2 right-0 w-2/3 h-px -translate-y-4 rotate-[-8deg] pointer-events-none"
          style={{ background: "linear-gradient(90deg, transparent, rgba(255,184,0,.5), transparent)" }}
        />
        <div className="relative w-[58px] h-[58px] rounded-full bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center font-display font-extrabold text-xl text-[#1A1408] flex-shrink-0">
          {account.initials}
        </div>
        <div className="relative flex-1 min-w-0">
          <div className="font-display font-bold text-[17px] text-ink">{account.name}</div>
          <div className="font-medium text-[13px] text-ink/45">{account.username}</div>
          <span className="inline-flex items-center gap-1.5 mt-1.5 bg-white/[.05] border border-white/[.08] rounded-full px-2.5 py-[3px]">
            <span
              className="w-[6px] h-[6px] rounded-full"
              style={{ background: subscription.active ? "#2ED9A6" : "rgba(245,243,238,.35)" }}
            />
            <span
              className="font-medium text-[11px]"
              style={{ color: subscription.active ? "#2ED9A6" : "rgba(245,243,238,.4)" }}
            >
              {subscription.active ? "Онлайн" : "Не активен"}
            </span>
          </span>
        </div>
        <GearIcon />
      </div>

      <div className="relative rounded-[20px] p-[18px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#120E06_0%,#0C0E12_60%)]">
        <svg
          viewBox="0 0 24 24"
          className="absolute top-3 right-3 w-16 h-16 opacity-90 pointer-events-none"
        >
          <ellipse cx="12" cy="12" rx="10.5" ry="4" fill="none" stroke="#FFB800" strokeOpacity=".3" strokeWidth=".6" transform="rotate(-18 12 12)" />
          <path
            d="M12 4l1.8 4.4L18.5 9l-3.5 3 1 4.6L12 14.2l-4 2.4 1-4.6-3.5-3 4.7-.6z"
            fill="url(#accountStarGrad)"
          />
          <defs>
            <linearGradient id="accountStarGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#FFD84D" />
              <stop offset="100%" stopColor="#CC8A00" />
            </linearGradient>
          </defs>
        </svg>

        <div className="relative font-semibold text-[13px] text-ink/55">Текущий план</div>
        <div className="relative flex items-center gap-2 mt-1.5">
          <span className="font-display font-extrabold text-2xl text-gold">{planLabel(subscription.planName)}</span>
          {subscription.active && (
            <span className="font-display font-bold text-[11px] text-ink/60 bg-white/[.06] px-2 py-1 rounded-lg">
              {subscription.daysLeft} дней
            </span>
          )}
        </div>

        <div className="relative flex items-center gap-2 mt-3.5">
          <CalendarIcon size={15} />
          <span className="font-medium text-[12.5px] text-ink/40">Продление</span>
          <span className="ml-auto font-semibold text-[13px] text-ink">{subscription.expiryDate}</span>
        </div>
        <div className="relative flex items-center gap-2 mt-2.5">
          <CardIcon size={15} />
          <span className="font-medium text-[12.5px] text-ink/40">Оплата</span>
          <span className="ml-auto flex items-center gap-1 font-semibold text-[13px] text-ink">
            <StarIcon size={11} /> Telegram Stars
          </span>
        </div>

        <button
          onClick={onManageSubscription}
          className="relative w-full mt-4 bg-gradient-to-br from-gold to-gold-dark py-3 rounded-[14px] flex items-center justify-center gap-2"
        >
          <CrownIcon size={16} color="#1A1408" />
          <span className="font-display font-bold text-[14px] text-[#1A1408]">Управлять подпиской</span>
          <ChevronIcon color="rgba(26,20,8,.5)" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={onOpenInstructions}
          className="bg-app-card border border-gold/20 rounded-lg p-2.5 text-left flex flex-col gap-2"
        >
          <div className="flex items-center justify-between">
            <div className="w-7 h-7 rounded-md bg-gold/[.08] border border-gold/20 flex items-center justify-center flex-shrink-0">
              <SettingIcon name="info" color="#FFB800" />
            </div>
            <ChevronIcon />
          </div>
          <div>
            <div className="font-semibold text-[12.5px] text-ink">Как подключиться</div>
            <div className="font-medium text-[10px] text-ink/40 mt-0.5">Инструкция для всех устройств</div>
          </div>
        </button>

        <button
          onClick={() => openExternal(`${account.siteUrl}/support`)}
          className="bg-app-card border border-gold/20 rounded-lg p-2.5 text-left flex flex-col gap-2"
        >
          <div className="flex items-center justify-between">
            <div className="w-7 h-7 rounded-md bg-gold/[.08] border border-gold/20 flex items-center justify-center flex-shrink-0">
              <HeadsetIcon size={16} />
            </div>
            <ChevronIcon />
          </div>
          <div>
            <div className="font-semibold text-[12.5px] text-ink">Написать в поддержку</div>
            <div className="font-medium text-[10px] text-ink/40 mt-0.5">Оформить заявку — ответим в боте</div>
          </div>
        </button>
      </div>

      <div>
        <div className="font-semibold text-[13px] text-ink/60 mb-2">Информация</div>
        <div className="bg-app-card border border-white/[.06] rounded-[18px] overflow-hidden">
          {INFO_ROWS.map((row, i) => (
            <button
              key={row.label}
              onClick={() => openExternal(account[row.urlKey])}
              className={`w-full flex items-center gap-3 px-4 py-3.5 text-left ${
                i < INFO_ROWS.length - 1 ? "border-b border-white/[.05]" : ""
              }`}
            >
              <div className="w-[30px] h-[30px] rounded-[9px] bg-white/[.05] flex items-center justify-center flex-shrink-0">
                {row.icon}
              </div>
              <span className="flex-1 font-medium text-[13.5px] text-ink">{row.label}</span>
              <span className="font-medium text-xs text-ink/35">→</span>
            </button>
          ))}
        </div>
      </div>

      <div className="bg-app-card border border-white/[.06] rounded-[18px] overflow-hidden">
        {settingsRows.map((row, i) => (
          <button
            key={row.id}
            onClick={() => onOpenSetting(row.id)}
            className={`w-full flex items-center gap-3 px-4 py-3.5 text-left ${
              i < settingsRows.length - 1 ? "border-b border-white/[.05]" : ""
            }`}
          >
            <div className="w-[30px] h-[30px] rounded-[9px] bg-white/[.05] flex items-center justify-center flex-shrink-0">
              <SettingIcon name={row.icon} color="#FFB800" />
            </div>
            <span className="flex-1 font-medium text-[13.5px] text-ink">{row.label}</span>
            {row.detail && <span className="font-medium text-xs text-ink/35 mr-1">{row.detail}</span>}
            <ChevronIcon />
          </button>
        ))}
      </div>

      <button
        onClick={onRefresh}
        disabled={refreshing}
        className="mx-auto flex items-center gap-1.5 py-2 px-3 font-medium text-xs text-ink/40 disabled:opacity-50"
      >
        <RefreshIcon />
        {refreshing ? "Обновляем…" : "Обновить данные"}
      </button>

      <button onClick={onLogout} className="border-none bg-transparent py-2 font-semibold text-[13px] text-danger text-center">
        Выйти из аккаунта
      </button>
      <div className="text-center font-medium text-[11px] text-ink/25 pb-1">
        STAR VPN · версия {account.appVersion}
      </div>
    </div>
  );
}
