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
  const customStars = Math.max(1, Math.round(customDays * pricePerDay));
  const customRub = Math.max(1, Math.round(customDays * rubPerDay));

  const selectedPlan = { label: `${customDays} дней`, days: customDays, price: customStars, rub: customRub };

  if (step === "success") {
    return (
      <BottomSheet open={open} onClose={onClose} maxHeight="82%">
        <div className="flex flex-col items-center text-center pt-5 pb-1.5">
          <div className="w-16 h-16 rounded-full bg-success/[.12] border border-success/30 flex items-center justify-center mb-4">
            <CheckIcon size={28} color="#2ED9A6" />
          </div>
          <div className="font-display font-extrabold text-[17px] text-ink">Подписка продлена!</div>
          <div className="font-medium text-[13.5px] text-ink/45 mt-1.5 max-w-[260px] inline-flex items-center gap-1 flex-wrap justify-center">
            Добавлено {lastAddedDays} дней. Спасибо, что выбираете STAR VPN <StarIcon size={12} />
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

      <div className="bg-app-card border border-white/10 rounded-2xl px-4 pt-4 pb-3.5">
        <div className="flex items-end justify-between">
          <div className="flex items-baseline gap-1.5">
            <span className="font-display font-extrabold text-[38px] leading-none text-ink">{customDays}</span>
            <span className="font-medium text-sm text-ink/40">дней</span>
          </div>
          <div className="text-right">
            {method === "stars" ? (
              <div className="flex items-center gap-1 justify-end">
                <StarIcon size={14} />
                <span className="font-display font-extrabold text-lg text-gold">{customStars}</span>
              </div>
            ) : (
              <span className="font-display font-extrabold text-lg text-[#5FD068]">{customRub} ₽</span>
            )}
            <div className="flex items-center gap-1 justify-end font-medium text-[11px] text-ink/35 mt-0.5">
              {method === "stars" ? (
                <>
                  {pricePerDay.toFixed(1)} <StarIcon size={9} /> в день
                </>
              ) : (
                `${rubPerDay.toFixed(1)} ₽ в день`
              )}
            </div>
          </div>
        </div>

        <input
          type="range"
          min="7"
          max="180"
          value={customDays}
          onChange={(e) => onCustomDaysChange(Number(e.target.value))}
          className="w-full mt-3.5 accent-gold"
        />
        <div className="flex justify-between mt-1 font-medium text-[10.5px] text-ink/30">
          <span>7 дней</span>
          <span>180 дней</span>
        </div>
      </div>

      <button
        onClick={onSubmit}
        className="w-full mt-[18px] border-none py-4 rounded-2xl flex items-center justify-center gap-2"
        style={{ background: method === "stars" ? "linear-gradient(135deg,#FFB800,#CC8A00)" : "linear-gradient(135deg,#5FD068,#3AA84A)" }}
      >
        {method === "stars" ? (
          <>
            <BoltIcon size={14} />
            <span className="font-display font-bold text-[15px] text-[#1A1408] inline-flex items-center gap-1">
              Оплатить {selectedPlan.price} <StarIcon size={13} color="#1A1408" />
            </span>
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
