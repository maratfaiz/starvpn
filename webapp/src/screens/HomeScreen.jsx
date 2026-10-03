import { StarIcon, BoltIcon, GiftIcon, LocationIcon } from "../components/icons.jsx";

export default function HomeScreen({
  subscription,
  server,
  trafficUsedTotal,
  autoServer,
  onToggleAutoServer,
  onOpenRenew,
  onOpenGift,
  onActivateTrial,
  trialActivating,
}) {
  const active = subscription.active;
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
      </div>

      {/* server + traffic */}
      {active && (
        <div className="grid grid-cols-[1.3fr_1fr] gap-2.5">
          <div className="bg-app-card border border-white/[.06] rounded-[18px] p-4 flex flex-col justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-sm">{server.flag}</span>
              <span className="font-semibold text-xs text-ink/50">текущий сервер</span>
            </div>
            <div>
              <div className="font-display font-bold text-base text-ink">{server.name}</div>
              <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">{server.protocol}</div>
            </div>
          </div>
          <div className="bg-app-card border border-white/[.06] rounded-[18px] p-3.5 flex flex-col justify-center">
            <div className="font-display font-extrabold text-[22px] text-ink">
              {trafficUsedTotal}
              <span className="text-[13px] text-ink/40"> ГБ</span>
            </div>
            <div className="font-medium text-[10.5px] text-ink/40 mt-0.5">трафика использовано</div>
          </div>
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

      {active && (
        <div className="flex items-center justify-between px-4 py-3.5 bg-app-card border border-white/[.06] rounded-2xl">
          <div className="flex items-center gap-2.5">
            <div className="w-[34px] h-[34px] rounded-[10px] bg-white/[.05] flex items-center justify-center">
              <LocationIcon />
            </div>
            <div>
              <div className="font-medium text-[13px] text-ink">Авто-выбор сервера</div>
              <div className="font-medium text-[11px] text-ink/40">Подключает самый быстрый узел</div>
            </div>
          </div>
          <button
            onClick={onToggleAutoServer}
            className="w-[42px] h-6 rounded-full relative flex-shrink-0"
            style={{ background: autoServer ? "linear-gradient(135deg,#F7CE68,#C9962F)" : "rgba(255,255,255,.1)" }}
            aria-pressed={autoServer}
          >
            <div
              className="absolute top-0.5 w-5 h-5 rounded-full bg-[#1A1408] transition-all"
              style={{ left: autoServer ? "20px" : "2px" }}
            />
          </button>
        </div>
      )}
    </div>
  );
}
