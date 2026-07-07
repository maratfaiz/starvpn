import BottomSheet from "../components/BottomSheet.jsx";
import { BoltIcon, StarIcon, CheckIcon } from "../components/icons.jsx";

export default function RenewSheet({ open, step, onClose, plans, selectedPlanId, onSelectPlan, onSubmit, lastAddedDays }) {
  const selectedPlan = plans.find((p) => p.id === selectedPlanId) || plans[0];

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
    <BottomSheet open={open} onClose={onClose} maxHeight="82%">
      <div className="flex items-center justify-between mb-[18px] -mt-1">
        <div className="flex items-center gap-2">
          <BoltIcon size={18} color="#F7CE68" />
          <span className="font-display font-extrabold text-base text-ink">Продлить подписку</span>
        </div>
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
                background: selected ? "rgba(247,206,104,.1)" : "#12151C",
                border: `1.5px solid ${selected ? "rgba(247,206,104,.5)" : "rgba(255,255,255,.06)"}`,
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
                <StarIcon size={13} />
                <span className="font-display font-extrabold text-base text-gold">{p.price}</span>
              </div>
            </button>
          );
        })}
      </div>

      <button
        onClick={onSubmit}
        className="w-full mt-[18px] border-none py-4 rounded-2xl bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
      >
        <BoltIcon size={14} />
        <span className="font-display font-bold text-[15px] text-[#1A1408]">Оплатить {selectedPlan.price} ⭐</span>
      </button>
      <div className="text-center font-medium text-[11.5px] text-ink/30 mt-2.5">Оплата через Telegram Stars</div>
    </BottomSheet>
  );
}
