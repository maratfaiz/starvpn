import BottomSheet from "../components/BottomSheet.jsx";
import { StarIcon, CheckIcon } from "../components/icons.jsx";

export default function TopupSheet({ open, step, onClose, packs, selectedPackId, onSelectPack, onSubmit, starsBalance }) {
  const selectedPack = packs.find((p) => p.id === selectedPackId) || packs[0];

  if (step === "success") {
    return (
      <BottomSheet open={open} onClose={onClose} maxHeight="82%">
        <div className="flex flex-col items-center text-center pt-5 pb-1.5">
          <div className="w-16 h-16 rounded-full bg-success/[.12] border border-success/30 flex items-center justify-center mb-4">
            <CheckIcon size={28} color="#2ED9A6" />
          </div>
          <div className="font-display font-extrabold text-[17px] text-ink">Баланс пополнен!</div>
          <div className="font-medium text-[13.5px] text-ink/45 mt-1.5 max-w-[260px]">
            +{selectedPack.stars} ⭐ зачислено на ваш счёт
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
      <div className="flex items-center justify-between mb-1.5 -mt-1">
        <div className="flex items-center gap-2">
          <StarIcon size={18} />
          <span className="font-display font-extrabold text-base text-ink">Пополнить баланс</span>
        </div>
      </div>
      <div className="font-medium text-[13px] text-ink/40 mb-4">Текущий баланс: {starsBalance} ⭐</div>

      <div className="grid grid-cols-2 gap-2.5">
        {packs.map((pack) => {
          const selected = pack.id === selectedPackId;
          return (
            <button
              key={pack.id}
              onClick={() => onSelectPack(pack.id)}
              className="relative px-3 py-4 rounded-2xl text-center"
              style={{
                background: selected ? "rgba(247,206,104,.1)" : "#12151C",
                border: `1.5px solid ${selected ? "rgba(247,206,104,.5)" : "rgba(255,255,255,.06)"}`,
              }}
            >
              {pack.best && (
                <span className="absolute -top-[9px] left-1/2 -translate-x-1/2 font-display font-bold text-[9.5px] text-[#1A1408] bg-gold px-2 py-0.5 rounded-full whitespace-nowrap">
                  ВЫГОДНО
                </span>
              )}
              <div className="flex items-center justify-center gap-1.5">
                <StarIcon size={15} />
                <span className="font-display font-extrabold text-lg text-ink">{pack.stars}</span>
              </div>
              <div className="font-semibold text-xs text-ink/40 mt-1.5">{pack.priceLabel}</div>
            </button>
          );
        })}
      </div>

      <button
        onClick={onSubmit}
        className="w-full mt-[18px] border-none py-4 rounded-2xl bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
      >
        <StarIcon size={14} color="#1A1408" />
        <span className="font-display font-bold text-[15px] text-[#1A1408]">
          Купить {selectedPack.stars} ⭐ за {selectedPack.priceLabel}
        </span>
      </button>
      <div className="text-center font-medium text-[11.5px] text-ink/30 mt-2.5">Оплата через Telegram Stars</div>
    </BottomSheet>
  );
}
