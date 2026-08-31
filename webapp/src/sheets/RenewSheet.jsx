import BottomSheet from "../components/BottomSheet.jsx";
import { BoltIcon, StarIcon, CheckIcon } from "../components/icons.jsx";

const CardIcon = ({ size = 14, color = "#5FD068" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="5" width="20" height="14" rx="2" />
    <line x1="2" y1="10" x2="22" y2="10" />
  </svg>
);

export default function RenewSheet({
  open,
  step,
  onClose,
  plans,
  selectedPlanId,
  onSelectPlan,
  method,
  onSelectMethod,
  customDays,
  onCustomDaysChange,
  onSubmit,
  lastAddedDays,
}) {
  const basePlan = plans[0];
  const pricePerDay = basePlan.price / basePlan.days;
  const rubPerDay = basePlan.rub / basePlan.days;
  const isCustom = selectedPlanId === "custom";
  const customStars = Math.max(1, Math.round(customDays * pricePerDay));
  const customRub = Math.max(1, Math.round(customDays * rubPerDay));

  const selectedPlan = isCustom
    ? { label: `${customDays} дней`, days: customDays, price: customStars, rub: customRub }
    : plans.find((p) => p.id === selectedPlanId) || basePlan;

  if (step === "success") {
    return (
      <BottomSheet open={open} onClose={onClose} maxHeight="82%">
        <div className="flex flex-col items-center text-center pt-5 pb-1.5">
          <div className="w-16 h-16 rounded-full bg-success/[.12] border border-success/30 flex items-center justify-center mb-4">
            <CheckIcon size={28} color="#2ED9A6" />
          </div>
          <div className="font-display font-extrabold text-[17px] text-ink">Подписка продлена!</div>
          <div className="font-medium text-[13.5px] text-ink/45 mt-1.5 max-w-[260px]">
            Добавлено {lastAddedDays} дней. Спасибо, что выбираете STAR VPN ⭐
          </div>
          <button
            onClick={onClose}
            className="w-full mt-5 border-none py-3.5 rounded-[14px] bg-gold/10 font-display font-bold text-sm text-gold"
          >
            Готово
          </button>
        </div>
      </BottomSheet>
    );
  }

  return (
    <BottomSheet open={open} onClose={onClose} maxHeight="86%">
      <div className="flex items-center justify-between mb-4 -mt-1">
        <div className="flex items-center gap-2">
          <BoltIcon size={18} color="#FFB800" />
          <span className="font-display font-extrabold text-base text-ink">Продлить подписку</span>
        </div>
      </div>

      <div className="flex gap-1.5 mb-4 bg-white/[.04] rounded-2xl p-1">
        <button
          onClick={() => onSelectMethod("stars")}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-display font-semibold text-[12.5px]"
          style={{ background: method === "stars" ? "rgba(255,184,0,.14)" : "transparent", color: method === "stars" ? "#FFB800" : "rgba(245,243,238,.5)" }}
        >
          <StarIcon size={12} color={method === "stars" ? "#FFB800" : "rgba(245,243,238,.5)"} /> Stars
        </button>
        <button
          onClick={() => onSelectMethod("card")}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-display font-semibold text-[12.5px]"
          style={{ background: method === "card" ? "rgba(95,208,104,.14)" : "transparent", color: method === "card" ? "#5FD068" : "rgba(245,243,238,.5)" }}
        >
          <CardIcon size={12} color={method === "card" ? "#5FD068" : "rgba(245,243,238,.5)"} /> Карта ₽
        </button>
      </div>

      <div className="flex flex-col gap-2.5">
        {plans.map((p) => {
          const selected = p.id === selectedPlanId;
          return (
            <button
              key={p.id}
              onClick={() => onSelectPlan(p.id)}
              className="relative flex items-center justify-between px-4 py-[15px] rounded-2xl"
              style={{
                background: selected ? "rgba(255,184,0,.1)" : "#12151C",
                border: `1.5px solid ${selected ? "rgba(255,184,0,.5)" : "rgba(255,255,255,.06)"}`,
              }}
            >
              {p.popular && (
                <span className="absolute -top-[9px] left-3.5 font-display font-bold text-[9.5px] text-[#1A1408] bg-gold px-2 py-0.5 rounded-full">
                  ВЫГОДНО
                </span>
              )}
              <div className="text-left">
                <div className="font-display font-bold text-[14.5px] text-ink">{p.label}</div>
                <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">{p.perMonth}</div>
              </div>
              <div className="flex items-center gap-1.5">
                {method === "stars" ? (
                  <>
                    <StarIcon size={13} />
                    <span className="font-display font-extrabold text-base text-gold">{p.price}</span>
                  </>
                ) : (
                  <span className="font-display font-extrabold text-base text-[#5FD068]">{p.rub} ₽</span>
                )}
              </div>
            </button>
          );
        })}

        <button
          onClick={() => onSelectPlan("custom")}
          className="relative flex items-center justify-between px-4 py-[15px] rounded-2xl"
          style={{
            background: isCustom ? "rgba(255,184,0,.1)" : "#12151C",
            border: `1.5px solid ${isCustom ? "rgba(255,184,0,.5)" : "rgba(255,255,255,.06)"}`,
          }}
        >
          <div className="text-left">
            <div className="font-display font-bold text-[14.5px] text-ink">Свой срок</div>
            <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">Укажи количество дней</div>
          </div>
          <div className="flex items-center gap-1.5">
            {method === "stars" ? (
              <>
                <StarIcon size={13} />
                <span className="font-display font-extrabold text-base text-gold">{customStars}</span>
              </>
            ) : (
              <span className="font-display font-extrabold text-base text-[#5FD068]">{customRub} ₽</span>
            )}
          </div>
        </button>

        {isCustom && (
          <div className="flex items-center gap-3 bg-app-card border border-white/10 rounded-2xl px-4 py-3">
            <input
              type="range"
              min="1"
              max="730"
              value={customDays}
              onChange={(e) => onCustomDaysChange(Number(e.target.value))}
              className="flex-1 accent-gold"
            />
            <input
              type="number"
              min="1"
              max="730"
              value={customDays}
              onChange={(e) => onCustomDaysChange(Math.max(1, Math.min(730, Number(e.target.value) || 1)))}
              className="w-16 bg-white/[.05] border border-white/10 rounded-lg px-2 py-1.5 text-center font-display font-bold text-sm text-ink outline-none"
            />
            <span className="font-medium text-xs text-ink/40 flex-shrink-0">дней</span>
          </div>
        )}
      </div>

      <button
        onClick={onSubmit}
        className="w-full mt-[18px] border-none py-4 rounded-2xl flex items-center justify-center gap-2"
        style={{ background: method === "stars" ? "linear-gradient(135deg,#FFB800,#CC8A00)" : "linear-gradient(135deg,#5FD068,#3AA84A)" }}
      >
        {method === "stars" ? (
          <>
            <BoltIcon size={14} />
            <span className="font-display font-bold text-[15px] text-[#1A1408]">Оплатить {selectedPlan.price} ⭐</span>
          </>
        ) : (
          <>
            <CardIcon size={14} color="#0A0D13" />
            <span className="font-display font-bold text-[15px] text-[#0A0D13]">Оплатить {selectedPlan.rub} ₽</span>
          </>
        )}
      </button>
      <div className="text-center font-medium text-[11.5px] text-ink/30 mt-2.5">
        {method === "stars" ? "Оплата через Telegram Stars" : "Visa · Mastercard · МИР — оплата через Robokassa"}
      </div>
    </BottomSheet>
  );
}
