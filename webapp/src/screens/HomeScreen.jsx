import { StarIcon, BoltIcon, GiftIcon, LocationIcon } from "../components/icons.jsx";

export default function HomeScreen({
  subscription,
  server,
  speedValue,
  trafficUsedTotal,
  autoServer,
  onToggleAutoServer,
  onOpenRenew,
  onOpenGift,
}) {
  const percentPassed = Math.round(
    ((subscription.totalDays - subscription.daysLeft) / subscription.totalDays) * 100
  );

  return (
    <div className="flex flex-col gap-4">
      {/* hero subscription card */}
      <div className="relative rounded-3xl p-[22px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#1A1408_0%,#13161D_55%)]">
        <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-[radial-gradient(circle,rgba(247,206,104,.25),transparent_70%)]" />
        <StarIcon size={11} className="absolute top-3.5 right-[18px] animate-[starTwinkle_2.6s_ease-in-out_infinite]" />
        <StarIcon size={7} className="absolute top-[46px] right-[54px] animate-[starTwinkle_3.2s_ease-in-out_.6s_infinite]" />

        <div className="relative flex items-center gap-1.5 mb-3.5">
          <div className="w-[7px] h-[7px] rounded-full bg-success animate-[pulseDot_1.8s_infinite]" />
          <span className="font-medium text-[12.5px] text-success tracking-wide">{subscription.connectionLabel}</span>
          <span className="ml-auto font-display font-semibold text-[11px] text-gold bg-gold/10 px-2.5 py-[3px] rounded-full border border-gold/25">
            {subscription.planName}
          </span>
        </div>

        <div className="relative flex items-end gap-2">
          <span className="font-display font-extrabold text-[56px] leading-[.9] text-ink">{subscription.daysLeft}</span>
          <span className="font-semibold text-[15px] text-ink/55 pb-2">дней осталось</span>
        </div>
        <div className="font-medium text-[13px] text-ink/40 mt-1">
          Подписка действует до {subscription.expiryDate}
        </div>

        <div className="mt-4 h-1.5 rounded-full bg-white/[.07] overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-gold-dark to-gold"
            style={{ width: `${percentPassed}%` }}
          />
        </div>
      </div>

      {/* server + quick stats bento */}
      <div className="grid grid-cols-[1.3fr_1fr] grid-rows-2 gap-2.5">
        <div className="row-span-2 bg-app-card border border-white/[.06] rounded-[18px] p-4 flex flex-col justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm">{server.flag}</span>
            <span className="font-semibold text-xs text-ink/50">текущий сервер</span>
          </div>
          <div>
            <div className="font-display font-bold text-base text-ink">{server.name}</div>
            <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">
              {server.ping} мс · {server.protocol}
            </div>
          </div>
          <span className="font-display font-bold text-xs text-gold">Сменить →</span>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-[18px] p-3.5">
          <div className="font-display font-extrabold text-[22px] text-ink">{speedValue}</div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-0.5">Мбит/с сейчас</div>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-[18px] p-3.5">
          <div className="font-display font-extrabold text-[22px] text-ink">
            {trafficUsedTotal}
            <span className="text-[13px] text-ink/40"> ГБ</span>
          </div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-0.5">за этот месяц</div>
        </div>
      </div>

      <div className="flex gap-2.5">
        <button
          onClick={onOpenRenew}
          className="flex-1 py-4 rounded-[18px] bg-gradient-to-br from-gold to-gold-dark shadow-gold flex items-center justify-center gap-2"
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
    </div>
  );
}
