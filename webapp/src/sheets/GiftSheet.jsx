import BottomSheet from "../components/BottomSheet.jsx";
import { GiftIcon, StarIcon, CheckIcon } from "../components/icons.jsx";

export default function GiftSheet({
  open,
  step,
  onClose,
  dayOptions,
  username,
  days,
  comment,
  onUsernameChange,
  onDaysSelect,
  onCommentChange,
  onSubmit,
}) {
  if (step === "success") {
    return (
      <BottomSheet open={open} onClose={onClose} maxHeight="78%">
        <div className="flex flex-col items-center text-center pt-5 pb-1.5">
          <div className="w-16 h-16 rounded-full bg-success/[.12] border border-success/30 flex items-center justify-center mb-4">
            <CheckIcon size={28} color="#2ED9A6" />
          </div>
          <div className="font-display font-extrabold text-[17px] text-ink">Подарок отправлен!</div>
          <div className="font-medium text-[13.5px] text-ink/45 mt-1.5 max-w-[260px]">
            {username} получит {days} дней VPN, как только примет подарок
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
    <BottomSheet open={open} onClose={onClose} maxHeight="78%">
      <div className="flex items-center justify-between mb-[18px] -mt-1">
        <div className="flex items-center gap-2">
          <GiftIcon size={18} />
          <span className="font-display font-extrabold text-base text-ink">Подарить VPN</span>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div>
          <div className="font-semibold text-[12.5px] text-ink/55 mb-1.5">
            Никнейм получателя <span className="text-gold">*</span>
          </div>
          <input
            value={username}
            onChange={(e) => onUsernameChange(e.target.value)}
            placeholder="@username"
            className="w-full bg-app-card border border-white/10 rounded-[13px] px-3.5 py-3 font-medium text-sm text-ink outline-none placeholder:text-ink/30"
          />
        </div>

        <div>
          <div className="font-semibold text-[12.5px] text-ink/55 mb-1.5">
            Количество дней <span className="text-gold">*</span>
          </div>
          <div className="flex gap-2">
            {dayOptions.map((opt) => {
              const selected = opt === days;
              return (
                <button
                  key={opt}
                  onClick={() => onDaysSelect(opt)}
                  className="flex-1 text-center py-2.5 rounded-xl"
                  style={{
                    background: selected ? "rgba(247,206,104,.1)" : "#12151C",
                    border: `1px solid ${selected ? "rgba(247,206,104,.5)" : "rgba(255,255,255,.06)"}`,
                  }}
                >
                  <span className="font-display font-bold text-[13.5px]" style={{ color: selected ? "#F7CE68" : "#F5F3EE" }}>
                    {opt}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="font-semibold text-[12.5px] text-ink/55 mb-1.5">
            Комментарий <span className="text-ink/35">(необязательно)</span>
          </div>
          <textarea
            value={comment}
            onChange={(e) => onCommentChange(e.target.value)}
            placeholder="С днём рождения! 🎉"
            rows={3}
            className="w-full resize-none bg-app-card border border-white/10 rounded-[13px] px-3.5 py-3 font-medium text-sm text-ink outline-none placeholder:text-ink/30"
          />
        </div>

        <button
          onClick={onSubmit}
          disabled={!username.trim()}
          className="border-none py-4 rounded-2xl flex items-center justify-center gap-2 disabled:opacity-40"
          style={{ background: username.trim() ? "linear-gradient(135deg,#F7CE68,#C9962F)" : "rgba(255,255,255,.08)" }}
        >
          <StarIcon size={15} color={username.trim() ? "#1A1408" : "#F5F3EE"} />
          <span className="font-display font-bold text-[15px]" style={{ color: username.trim() ? "#1A1408" : "#F5F3EE" }}>
            Подарить {days} дней
          </span>
        </button>
      </div>
    </BottomSheet>
  );
}
