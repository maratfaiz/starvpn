import { useMemo } from "react";
import { GiftIcon, CheckIcon } from "./icons.jsx";

const COLORS = ["#FFB800", "#FF6B6B", "#4ECDC4", "#A8E6CF", "#FFD93D", "#6BCB77", "#4D96FF", "#FF6B9D"];

function Confetti() {
  const pieces = useMemo(
    () =>
      Array.from({ length: 48 }, (_, i) => {
        const size = 5 + Math.random() * 7;
        return {
          id: i,
          left: Math.random() * 100,
          width: size,
          height: size * (Math.random() > 0.5 ? 1 : 2.2),
          radius: Math.random() > 0.5 ? "50%" : "2px",
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
          duration: 1.2 + Math.random() * 1.8,
          delay: Math.random() * 0.6,
        };
      }),
    []
  );

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-3xl" aria-hidden="true">
      {pieces.map((p) => (
        <div
          key={p.id}
          className="absolute -top-2.5 opacity-90"
          style={{
            left: `${p.left}%`,
            width: p.width,
            height: p.height,
            borderRadius: p.radius,
            background: p.color,
            animation: `confettiFall ${p.duration}s cubic-bezier(.25,.46,.45,.94) ${p.delay}s forwards`,
          }}
        />
      ))}
    </div>
  );
}

export default function GiftReceivedModal({ gift, onClose }) {
  if (!gift) return null;

  return (
    <div className="fixed inset-0 z-[90] bg-black/60 flex items-center justify-center p-5" onClick={onClose}>
      <div
        className="relative w-full max-w-[340px] rounded-3xl border border-gold/30 bg-[linear-gradient(160deg,#1A1408_0%,#13161D_60%)] p-6 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Confetti />
        <div className="relative flex flex-col items-center text-center">
          <button
            onClick={onClose}
            className="absolute -top-1 -right-1 w-7 h-7 rounded-[9px] bg-white/[.06] border border-white/[.08] flex items-center justify-center text-ink/50 text-xs"
          >
            ✕
          </button>
          <div className="w-16 h-16 rounded-full bg-gold/10 border border-gold/25 flex items-center justify-center mb-4">
            <GiftIcon size={30} />
          </div>
          <div className="font-display font-extrabold text-lg text-ink">Тебе подарили VPN!</div>
          <div className="font-medium text-[13px] text-ink/50 mt-1">
            от <span className="text-gold font-semibold">{gift.from_name || "Аноним"}</span>
          </div>

          <div className="w-full grid grid-cols-2 gap-2.5 mt-5">
            <div className="bg-white/[.04] border border-white/[.08] rounded-2xl px-3 py-3 text-center">
              <div className="font-medium text-[10.5px] text-ink/40 mb-1">Тариф</div>
              <div className="font-display font-bold text-[13px] text-ink">{gift.plan_label}</div>
            </div>
            <div className="bg-white/[.04] border border-white/[.08] rounded-2xl px-3 py-3 text-center">
              <div className="font-medium text-[10.5px] text-ink/40 mb-1">Длительность</div>
              <div className="font-display font-bold text-[13px] text-ink">{gift.days} дней</div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full mt-6 py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
          >
            <CheckIcon size={15} color="#1A1408" />
            <span className="font-display font-bold text-[14px] text-[#1A1408]">Отлично, подключиться!</span>
          </button>
        </div>
      </div>
    </div>
  );
}
