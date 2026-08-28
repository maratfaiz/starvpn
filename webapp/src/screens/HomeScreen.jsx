import { StarIcon, BoltIcon, GiftIcon } from "../components/icons.jsx";

const stroke = {
  fill: "none",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

const KeyIcon = ({ size = 17 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" stroke="#FFB800" {...stroke}>
    <circle cx="7.5" cy="15.5" r="4" />
    <path d="M10.5 12.5L20 3M17 6l2.5 2.5M14.5 8.5L17 11" />
  </svg>
);

const QrIcon = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" stroke="#FFB800" {...stroke}>
    <rect x="3" y="3" width="7" height="7" rx="1.5" />
    <rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" />
    <path d="M14 14h3v3h-3zM20 14v1M14 20h3M20 19v2" />
  </svg>
);

const CopyIcon = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" stroke="#EBE0CC" {...stroke}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15V5a2 2 0 012-2h10" />
  </svg>
);

const TrafficIcon = ({ size = 21 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" stroke="#FFB800" {...stroke} strokeWidth={1.8}>
    <path d="M7 20V8M7 8L3.5 11.5M7 8l3.5 3.5" />
    <path d="M17 4v12M17 16l3.5-3.5M17 16l-3.5-3.5" />
  </svg>
);

const PlusIcon = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" stroke="#FFB800" {...stroke} strokeWidth={2.2}>
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

export default function HomeScreen({
  subscription,
  devices,
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
  // Ключ показываем для первого слота — он же используется чаще всего.
  // Остальные устройства живут на вкладке «Устройства».
  const primary = devices[0] || null;
  const slotsLeft = devicesLimit - devices.length;
  // Полоса заполнена настолько, сколько подписки ОСТАЛОСЬ: заполненная
  // шкала у свежей подписки читается лучше, чем «сколько уже прошло».
  const percentLeft = active && subscription.totalDays
    ? Math.max(0, Math.min(100, Math.round((subscription.daysLeft / subscription.totalDays) * 100)))
    : 0;
  const showTrialCard = !active && !subscription.trialUsed;

  return (
    <div className="flex flex-col gap-4">
      {/* hero subscription card */}
      <div className="relative rounded-3xl p-[22px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#1A1408_0%,#100E0A_55%)]">
        <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-[radial-gradient(circle,rgba(255,184,0,.25),transparent_70%)]" />
        <StarIcon size={11} className="absolute top-3.5 right-[18px] animate-[starTwinkle_2.6s_ease-in-out_infinite]" />
        <StarIcon size={7} className="absolute top-[46px] right-[54px] animate-[starTwinkle_3.2s_ease-in-out_.6s_infinite]" />

        <div className="relative flex items-center gap-1.5 mb-3.5">
          <div
            className="w-[7px] h-[7px] rounded-full"
            style={{ background: active ? "#4ADE80" : "rgba(235,224,204,.35)" }}
          />
          <span
            className="font-medium text-[12.5px] tracking-wide"
            style={{ color: active ? "#4ADE80" : "rgba(235,224,204,.45)" }}
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

        {active && (
          <>
            <div className="relative flex items-center justify-between mt-4 mb-1.5">
              <span className="font-medium text-[11.5px] text-ink/40">Осталось</span>
              <span className="font-display font-bold text-[12px] text-gold tabular-nums">
                {percentLeft}%
              </span>
            </div>
            <div className="relative h-1.5 rounded-full bg-white/[.07] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-gold-dark to-gold"
                style={{ width: `${percentLeft}%` }}
              />
            </div>

            {/* Действия живут в той же карточке, что и срок: продлевают
                именно его, отдельным блоком ниже они читались как не
                связанные с подпиской. */}
            <div className="relative flex gap-2.5 mt-[18px]">
              <button
                onClick={onOpenRenew}
                className="flex-1 py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
              >
                <BoltIcon size={14} />
                <span className="font-display font-bold text-[13.5px] text-[#1A1408]">Продлить</span>
              </button>
              <button
                onClick={onOpenGift}
                className="flex-1 py-3.5 rounded-2xl border-[1.5px] border-gold/35 bg-gold/[.08] flex items-center justify-center gap-2"
              >
                <GiftIcon size={14} />
                <span className="font-display font-bold text-[13.5px] text-gold">Подарить</span>
              </button>
            </div>
          </>
        )}
      </div>

      {/* Ключ и подключение — то, что нужно сразу после оплаты.
          Раньше здесь стояли карточка сервера с пингом, кнопка «Сменить»
          и спидометр: ни пинг, ни скорость приложение измерить не может,
          а второго сервера и эндпоинта смены не существует. */}
      {active && (
        <>
          {primary ? (
            <div className="bg-app-card border border-white/[.06] rounded-[18px] p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[11px] tracking-[.14em] uppercase text-ink/40">
                  Ваш ключ
                </span>
                <span className="font-medium text-[11.5px] text-ink/35">
                  {devices.length} из {devicesLimit} устройств
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-[11px] bg-white/[.05] flex items-center justify-center flex-shrink-0">
                  <KeyIcon />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-[13.5px] text-ink truncate">{primary.name}</div>
                  <div className="font-medium text-[11.5px] text-ink/40">слот {primary.slot}</div>
                </div>
              </div>

              <div className="flex gap-2.5">
                <button
                  onClick={() => onShowKey(primary)}
                  className="flex-1 py-3 rounded-[14px] bg-gold/[.10] border border-gold/30 flex items-center justify-center gap-2"
                >
                  <QrIcon />
                  <span className="font-display font-bold text-[13px] text-gold">Показать QR</span>
                </button>
                <button
                  onClick={() => onCopyKey(primary)}
                  className="flex-1 py-3 rounded-[14px] bg-white/[.05] border border-white/[.08] flex items-center justify-center gap-2"
                >
                  <CopyIcon />
                  <span className="font-display font-bold text-[13px] text-ink/75">Копировать</span>
                </button>
              </div>
            </div>
          ) : (
            /* Подписка есть, а устройств нет — самый важный момент:
               человеку нужен первый ключ, всё остальное подождёт. */
            <button
              onClick={onAddDevice}
              className="rounded-[18px] border-[1.5px] border-gold/40 bg-gold/[.07] px-4 py-5 flex flex-col items-center gap-2"
            >
              <QrIcon size={26} />
              <span className="font-display font-bold text-[15px] text-gold">Подключить устройство</span>
              <span className="font-medium text-[12px] text-ink/45 text-center">
                Получи ключ и вставь его в VPN-клиент
              </span>
            </button>
          )}

          <div className="flex items-center gap-3.5 px-4 py-4 bg-app-card border border-white/[.06] rounded-[18px]">
            <div className="w-11 h-11 rounded-[13px] bg-gold/[.10] border border-gold/20 flex items-center justify-center flex-shrink-0">
              <TrafficIcon />
            </div>
            <div className="min-w-0">
              <div className="font-medium text-[11.5px] tracking-[.12em] uppercase text-ink/40">
                Трафик за месяц
              </div>
              <div className="font-display font-extrabold text-[26px] leading-tight text-ink tabular-nums">
                {trafficUsedTotal}
                <span className="font-bold text-[15px] text-ink/45"> ГБ</span>
              </div>
            </div>
          </div>
        </>
      )}

      {active && primary && slotsLeft > 0 && (
        <button
          onClick={onAddDevice}
          className="border-[1.5px] border-dashed border-gold/35 py-3.5 rounded-2xl bg-gold/[.05] flex items-center justify-center gap-2"
        >
          <PlusIcon />
          <span className="font-display font-bold text-[13.5px] text-gold">
            Подключить ещё устройство
          </span>
        </button>
      )}

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

    </div>
  );
}
