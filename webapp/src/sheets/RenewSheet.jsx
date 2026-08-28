import BottomSheet from "../components/BottomSheet.jsx";
import { BoltIcon, StarIcon, CheckIcon } from "../components/icons.jsx";
import { dayWord } from "../utils/plural.js";

const CardIcon = ({ size = 14, color = "#4ADE80" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="5" width="20" height="14" rx="2" />
    <line x1="2" y1="10" x2="22" y2="10" />
  </svg>
);

// Диапазон и пресеты повторяют блок «Свой срок» на сайте
// (landing/tariffs.html): от 7 до 180 дней по той же дневной ставке.
const CUSTOM_MIN = 7;
const CUSTOM_MAX = 180;
const CUSTOM_PRESETS = [7, 30, 90, 180];

const clampDays = (raw) =>
  Math.max(CUSTOM_MIN, Math.min(CUSTOM_MAX, Number(raw) || CUSTOM_MIN));

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
    ? { label: `${customDays} ${dayWord(customDays)}`, days: customDays, price: customStars, rub: customRub }
    : plans.find((p) => p.id === selectedPlanId) || basePlan;

  if (step === "success") {
    return (
      <BottomSheet open={open} onClose={onClose} maxHeight="82%">
        <div className="flex flex-col items-center text-center pt-5 pb-1.5">
          <div className="w-16 h-16 rounded-full bg-success/[.12] border border-success/30 flex items-center justify-center mb-4">
            <CheckIcon size={28} color="#4ADE80" />
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
          style={{ background: method === "stars" ? "rgba(255,184,0,.14)" : "transparent", color: method === "stars" ? "#FFB800" : "rgba(235,224,204,.5)" }}
        >
          <StarIcon size={12} color={method === "stars" ? "#FFB800" : "rgba(235,224,204,.5)"} /> Stars
        </button>
        <button
          onClick={() => onSelectMethod("card")}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-display font-semibold text-[12.5px]"
          style={{ background: method === "card" ? "rgba(95,208,104,.14)" : "transparent", color: method === "card" ? "#4ADE80" : "rgba(235,224,204,.5)" }}
        >
          <CardIcon size={12} color={method === "card" ? "#4ADE80" : "rgba(235,224,204,.5)"} /> Карта ₽
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
                background: selected ? "rgba(255,184,0,.1)" : "#0D0C0A",
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
                  <span className="font-display font-extrabold text-base text-[#4ADE80]">{p.rub} ₽</span>
                )}
              </div>
            </button>
          );
        })}

        <button
          onClick={() => onSelectPlan("custom")}
          className="relative flex items-center justify-between px-4 py-[15px] rounded-2xl"
          style={{
            background: isCustom ? "rgba(255,184,0,.1)" : "#0D0C0A",
            border: `1.5px solid ${isCustom ? "rgba(255,184,0,.5)" : "rgba(255,255,255,.06)"}`,
          }}
        >
          <div className="text-left">
            <div className="font-display font-bold text-[14.5px] text-ink">Свой срок</div>
            <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">От {CUSTOM_MIN} до {CUSTOM_MAX} дней</div>
          </div>
          <div className="flex items-center gap-1.5">
            {method === "stars" ? (
              <>
                <StarIcon size={13} />
                <span className="font-display font-extrabold text-base text-gold">{customStars}</span>
              </>
            ) : (
              <span className="font-display font-extrabold text-base text-[#4ADE80]">{customRub} ₽</span>
            )}
          </div>
        </button>

        {isCustom && (
          <div className="bg-app-card border border-gold/20 rounded-2xl px-4 py-4">
            {/* Число дней и цена в одной строке — то же построение, что в
                блоке «Свой срок» на странице тарифов сайта. */}
            <div className="flex items-end justify-between gap-3 mb-3">
              <div className="flex items-baseline gap-2 min-w-0">
                <input
                  type="number"
                  inputMode="numeric"
                  min={CUSTOM_MIN}
                  max={CUSTOM_MAX}
                  value={customDays}
                  onChange={(e) => onCustomDaysChange(clampDays(e.target.value))}
                  aria-label="Количество дней"
                  // Ширина по числу цифр, иначе между «7» и словом «дней»
                  // остаётся дыра шириной в трёхзначное число.
                  style={{ width: `${String(customDays).length + 0.6}ch` }}
                  className="bg-transparent border-0 p-0 font-display font-extrabold text-[38px] leading-none text-ink outline-none tabular-nums focus:text-gold"
                />
                <span className="font-medium text-[14px] text-ink/45">{dayWord(customDays)}</span>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="flex items-center justify-end gap-1.5">
                  {method === "stars" ? (
                    <>
                      <StarIcon size={13} />
                      <span className="font-display font-extrabold text-[22px] text-gold leading-none tabular-nums">
                        {customStars}
                      </span>
                    </>
                  ) : (
                    <span className="font-display font-extrabold text-[22px] text-[#4ADE80] leading-none tabular-nums">
                      {customRub} ₽
                    </span>
                  )}
                </div>
                <div className="font-medium text-[11px] text-ink/35 mt-1 tabular-nums">
                  {method === "stars"
                    ? `${(customStars / customDays).toFixed(1)} ⭐ в день`
                    : `${(customRub / customDays).toFixed(1)} ₽ в день`}
                </div>
              </div>
            </div>

            <input
              type="range"
              min={CUSTOM_MIN}
              max={CUSTOM_MAX}
              value={customDays}
              onChange={(e) => onCustomDaysChange(Number(e.target.value))}
              aria-label="Срок подписки в днях"
              className="star-slider"
            />
            <div className="flex justify-between font-mono text-[10.5px] text-ink/30 mt-0.5 mb-3">
              <span>{CUSTOM_MIN} дней</span>
              <span>90 дней</span>
              <span>{CUSTOM_MAX} дней</span>
            </div>

            {/* Пресеты: попасть пальцем в точное значение на узком экране
                тяжело, а эти четыре срока покрывают почти все случаи. */}
            <div className="grid grid-cols-4 gap-2">
              {CUSTOM_PRESETS.map((d) => {
                const picked = customDays === d;
                return (
                  <button
                    key={d}
                    onClick={() => onCustomDaysChange(d)}
                    className="py-2 rounded-xl font-display font-bold text-[12.5px] transition-colors"
                    style={{
                      background: picked ? "rgba(255,184,0,.14)" : "rgba(255,255,255,.04)",
                      border: `1px solid ${picked ? "rgba(255,184,0,.45)" : "rgba(255,255,255,.07)"}`,
                      color: picked ? "#FFB800" : "rgba(235,224,204,.55)",
                    }}
                  >
                    {d} дн.
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <button
        onClick={onSubmit}
        className="w-full mt-[18px] border-none py-4 rounded-2xl flex items-center justify-center gap-2"
        style={{ background: method === "stars" ? "linear-gradient(135deg,#FFB800,#D99B00)" : "linear-gradient(135deg,#4ADE80,#2F9E58)" }}
      >
        {method === "stars" ? (
          <>
            <BoltIcon size={14} />
            <span className="font-display font-bold text-[15px] text-[#1A1408]">Оплатить {selectedPlan.price} ⭐</span>
          </>
        ) : (
          <>
            <CardIcon size={14} color="#0A0908" />
            <span className="font-display font-bold text-[15px] text-[#0A0908]">Оплатить {selectedPlan.rub} ₽</span>
          </>
        )}
      </button>
      <div className="text-center font-medium text-[11.5px] text-ink/30 mt-2.5">
        {method === "stars" ? "Оплата через Telegram Stars" : "Visa · Mastercard · МИР — оплата через Robokassa"}
      </div>
    </BottomSheet>
  );
}
