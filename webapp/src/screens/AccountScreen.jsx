import { StarIcon, GearIcon, SettingIcon, ChevronIcon } from "../components/icons.jsx";

export default function AccountScreen({ account, subscription, settingsRows, onOpenSetting, onManageSubscription, onLogout, onOpenInstructions }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3.5 px-0.5 py-1.5">
        <div className="w-[58px] h-[58px] rounded-full bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center font-display font-extrabold text-xl text-[#1A1408] flex-shrink-0">
          {account.initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-display font-bold text-[17px] text-ink">{account.name}</div>
          <div className="font-medium text-[13px] text-ink/45">{account.username}</div>
        </div>
        <GearIcon />
      </div>

      <div className="rounded-[20px] p-[18px] border border-gold/30 bg-[linear-gradient(160deg,#1A1408_0%,#13161D_60%)]">
        <div className="flex justify-between items-center">
          <span className="font-semibold text-[13px] text-ink/55">Текущий план</span>
          <span className="font-display font-bold text-[13px] text-gold bg-gold/[.12] px-2.5 py-1 rounded-lg">
            {subscription.planName}
          </span>
        </div>
        <div className="flex justify-between items-center mt-2.5">
          <span className="font-medium text-[12.5px] text-ink/40">Продление</span>
          <span className="font-semibold text-[13px] text-ink">{subscription.expiryDate}</span>
        </div>
        <div className="flex justify-between items-center mt-2">
          <span className="font-medium text-[12.5px] text-ink/40">Оплата</span>
          <span className="flex items-center gap-1 font-semibold text-[13px] text-ink">
            <StarIcon size={11} /> Telegram Stars
          </span>
        </div>
        <button
          onClick={onManageSubscription}
          className="w-full mt-3.5 border border-gold/35 bg-gold/[.08] py-2.5 rounded-[13px] font-display font-bold text-[13px] text-gold"
        >
          Управлять подпиской
        </button>
      </div>

      <button
        onClick={onOpenInstructions}
        className="w-full flex items-center gap-3 bg-app-card border border-gold/20 rounded-2xl px-4 py-3.5 text-left"
      >
        <div className="w-9 h-9 rounded-[10px] bg-gold/[.08] border border-gold/20 flex items-center justify-center flex-shrink-0">
          <SettingIcon name="info" color="#F7CE68" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-[13.5px] text-ink">Как подключиться</div>
          <div className="font-medium text-[11px] text-ink/40">Пошаговая инструкция для всех устройств</div>
        </div>
        <ChevronIcon />
      </button>

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
              <SettingIcon name={row.icon} />
            </div>
            <span className="flex-1 font-medium text-[13.5px] text-ink">{row.label}</span>
            {row.detail && <span className="font-medium text-xs text-ink/35 mr-1">{row.detail}</span>}
            <ChevronIcon />
          </button>
        ))}
      </div>

      <button onClick={onLogout} className="border-none bg-transparent py-2 font-semibold text-[13px] text-danger text-center">
        Выйти из аккаунта
      </button>
      <div className="text-center font-medium text-[11px] text-ink/25 pb-1">
        STAR VPN · версия {account.appVersion}
      </div>
    </div>
  );
}
