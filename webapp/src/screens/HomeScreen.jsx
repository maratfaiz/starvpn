import { StarIcon, BoltIcon, GiftIcon, KeyIcon, QrIcon, CopyIcon } from "../components/icons.jsx";

export default function HomeScreen({
  subscription,
  primaryDevice,
  devicesCount,
  devicesLimit,
  trafficUsedTotal,
  onShowKey,
  onCopyKey,
  onAddDevice,
  onOpenRenew,
  onOpenGift,
  onActivateTrial,
  trialActivating,
}) {
  const active = subscription.active;
  const percentPassed = active
    ? Math.round(((subscription.totalDays - subscription.daysLeft) / subscription.totalDays) * 100)
    : 0;
  const showTrialCard = !active && !subscription.trialUsed;

  return (
    <div className="flex flex-col gap-4">
      {/* hero subscription card */}
      <div className="relative rounded-3xl p-[22px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#1A1408_0%,#13161D_55%)]">
        <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-[radial-gradient(circle,rgba(247,206,104,.25),transparent_70%)]" />
        <StarIcon size={11} className="absolute top-3.5 right-[18px] animate-[starTwinkle_2.6s_ease-in-out_infinite]" />
        <StarIcon size={7} className="absolute top-[46px] right-[54px] animate-[starTwinkle_3.2s_ease-in-out_.6s_infinite]" />

        <div className="relative flex items-center gap-1.5 mb-3.5">
          <div
            className="w-[7px] h-[7px] rounded-full"
            style={{ background: active ? "#2ED9A6" : "rgba(245,243,238,.35)" }}
          />
          <span
            className="font-medium text-[12.5px] tracking-wide"
            style={{ color: active ? "#2ED9A6" : "rgba(245,243,238,.45)" }}
          >
            {active ? subscription.connectionLabel : "Нет подписки"}
          </span>
          {active && (
            <span className="ml-auto font-display font-semibold text-[11px] text-gold bg-gold/10 px-2.5 py-[3px] rounded-full border border-gold/25">
              {subscription.planName}
            </span>
          )}
        </div>

        <div className="relative flex items-end gap-2">
          <span className="font-display font-extrabold text-[56px] leading-[.9] text-ink">
            {active ? subscription.daysLeft : "—"}
          </span>
          <span className="font-semibold text-[15px] text-ink/55 pb-2">дней осталось</span>
        </div>
        <div className="font-medium text-[13px] text-ink/40 mt-1">
          {active ? `Подписка действует до ${subscription.expiryDate}` : "Оформи подписку, чтобы подключиться"}
        </div>

        <div className="mt-4 h-1.5 rounded-full bg-white/[.07] overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-gold-dark to-gold"
            style={{ width: `${percentPassed}%` }}
          />
        </div>
      </div>

      {/* subscription key card */}
      {active && primaryDevice && (
        <div className="bg-app-card border border-white/[.06] rounded-[18px] p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="font-display font-semibold text-[11px] text-ink/40 tracking-widest uppercase">
              Ваш ключ
            </span>
            <span className="font-medium text-xs text-ink/40">
              {devicesCount} из {devicesLimit} устройств
            </span>
          </div>

          <div className="flex items-center gap-3 mb-4">
            <div className="w-[38px] h-[38px] rounded-[11px] bg-white/[.05] flex items-center justify-center flex-shrink-0">
              <KeyIcon size={17} />
            </div>
            <div className="min-w-0">
              <div className="font-display font-bold text-base text-ink truncate">{primaryDevice.name}</div>
              <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">слот {primaryDevice.slot}</div>
            </div>
          </div>

          <div className="flex gap-2.5">
            <button
              onClick={() => onShowKey(primaryDevice)}
              className="flex-1 py-3 rounded-[14px] border border-gold/35 bg-gold/[.08] flex items-center justify-center gap-2"
            >
              <QrIcon size={14} />
              <span className="font-display font-bold text-[13px] text-gold">Показать QR</span>
            </button>
            <button
              onClick={() => onCopyKey(primaryDevice)}
              className="flex-1 py-3 rounded-[14px] border border-white/10 flex items-center justify-center gap-2"
            >
              <CopyIcon size={14} />
              <span className="font-display font-bold text-[13px] text-ink/70">Копировать</span>
            </button>
          </div>
        </div>
      )}

      {active && (
        <div className="flex items-center justify-between px-4 py-3.5 bg-app-card border border-white/[.06] rounded-2xl">
          <span className="font-medium text-[13px] text-ink/60">Трафик за месяц</span>
          <span className="font-display font-bold text-[15px] text-ink">
            {trafficUsedTotal}
            <span className="text-ink/40 text-[12px]"> ГБ</span>
          </span>
        </div>
      )}

      <div className="flex gap-2.5">
        <button
          onClick={onOpenRenew}
          className="flex-1 py-4 rounded-[18px] bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
        >
          <BoltIcon size={15} />
          <span className="font-display font-bold text-[14.5px] text-[#1A1408]">Продлить</span>
        </button>
        <button
          onClick={onOpenGift}
          className="flex-1 py-4 rounded-[18px] border-[1.5px] border-gold/35 bg-gold/[.08] flex items-center justify-center gap-2"
        >
          <GiftIcon size={15} />
          <span className="font-display font-bold text-[14.5px] text-gold">Подарить VPN</span>
        </button>
      </div>

      {showTrialCard && (
        <div className="rounded-2xl border border-gold/40 bg-app-card text-center px-4 py-5">
          <div className="text-[28px] mb-2">🎁</div>
          <div className="font-display font-bold text-[15px] text-ink mb-1.5">Попробуй бесплатно — 2 дня</div>
          <div className="font-medium text-xs text-ink/45 mb-3.5">Полный безлимит · без ограничений</div>
          <button
            onClick={onActivateTrial}
            disabled={trialActivating}
            className="w-full py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <BoltIcon size={14} />
            <span className="font-display font-bold text-[13.5px] text-[#1A1408]">
              {trialActivating ? "Активируем…" : "Активировать тест"}
            </span>
          </button>
        </div>
      )}

      {active && devicesCount < devicesLimit && (
        <button
          onClick={onAddDevice}
          className="w-full py-3.5 rounded-2xl border-[1.5px] border-dashed border-gold/35 flex items-center justify-center gap-2"
        >
          <span className="font-display font-bold text-[15px] text-gold">+</span>
          <span className="font-display font-bold text-[13.5px] text-gold">Подключить ещё устройство</span>
        </button>
      )}
    </div>
  );
}
