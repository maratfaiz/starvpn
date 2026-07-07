import { StarIcon } from "./icons.jsx";

export default function Header({ starsBalance, onOpenTopup }) {
  return (
    <div className="flex items-center justify-between px-5 pt-5 pb-3 flex-shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-[30px] h-[30px] rounded-[9px] bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center shadow-gold">
          <StarIcon size={16} color="#0A0D13" />
        </div>
        <span className="font-display font-extrabold text-base text-ink tracking-tight">STAR VPN</span>
      </div>
      <button
        onClick={onOpenTopup}
        className="flex items-center gap-1.5 bg-gold/10 border border-gold/25 px-2.5 py-1.5 rounded-full"
      >
        <StarIcon size={13} />
        <span className="font-display font-bold text-[13px] text-gold">{starsBalance}</span>
      </button>
    </div>
  );
}
