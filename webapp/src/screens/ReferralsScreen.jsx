import { StarIcon, ShareIcon } from "../components/icons.jsx";

const HISTORY_ICON = {
  referral: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F7CE68" strokeWidth="2">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.5 19c0-3.2 2.9-5.5 6.5-5.5s6.5 2.3 6.5 5.5" />
    </svg>
  ),
  bonus: <StarIcon size={14} />,
  purchase: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F7CE68" strokeWidth="2">
      <path d="M13 2L3 14h7l-1 8 11-13h-7l1-7z" />
    </svg>
  ),
};

export default function ReferralsScreen({ referral, rewardTiers, daysHistory, copied, onCopyCode, onShare }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="relative rounded-3xl p-[22px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#1A1408_0%,#13161D_60%)]">
        <StarIcon size={10} className="absolute top-4 right-5 animate-[starTwinkle_2.4s_ease-in-out_infinite]" />
        <div className="font-display font-extrabold text-[19px] text-ink leading-tight max-w-[230px]">
          Приглашайте друзей — получайте дни VPN бесплатно
        </div>
        <div className="font-medium text-[13px] text-ink/50 mt-2">
          +{referral.bonusDays} дней за каждого друга, который оформит подписку
        </div>

        <div className="mt-[18px] flex items-center gap-2 bg-white/[.05] border border-white/[.08] rounded-[14px] px-3.5 py-3">
          <span className="flex-1 font-bold text-[15px] text-gold tracking-wider font-mono">{referral.code}</span>
          <button
            onClick={onCopyCode}
            className="font-display font-semibold text-xs text-[#1A1408] bg-gold px-3 py-1.5 rounded-[10px]"
          >
            {copied ? "Скопировано" : "Копировать"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2.5">
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 px-2 text-center">
          <div className="font-display font-extrabold text-[19px] text-ink">{referral.invitedCount}</div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-1">приглашено</div>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 px-2 text-center">
          <div className="font-display font-extrabold text-[19px] text-ink">{referral.daysEarned}</div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-1">дней получено</div>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 px-2 text-center">
          <div className="font-display font-extrabold text-[19px] text-gold">{referral.starsEarned}</div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-1">stars бонус</div>
        </div>
      </div>

      <div className="bg-app-card border border-white/[.06] rounded-2xl px-4 py-3.5">
        <div className="font-semibold text-[13px] text-ink/60 mb-2.5">Уровни наград</div>
        {rewardTiers.map((tier, i) => (
          <div
            key={tier.id}
            className={`flex items-center gap-2.5 py-2 ${i < rewardTiers.length - 1 ? "border-b border-white/[.05]" : ""}`}
          >
            <div className="w-7 h-7 rounded-[9px] bg-gold/10 flex items-center justify-center font-display font-bold text-[11px] text-gold flex-shrink-0">
              {tier.count}
            </div>
            <span className="flex-1 font-medium text-[12.5px] text-ink">{tier.label}</span>
            <span className="font-display font-semibold text-xs text-ink/45">{tier.reward}</span>
          </div>
        ))}
      </div>

      <button
        onClick={onShare}
        className="border-none py-[15px] rounded-[18px] bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
      >
        <ShareIcon />
        <span className="font-display font-bold text-[14.5px] text-[#1A1408]">Поделиться ссылкой</span>
      </button>

      <div>
        <div className="font-semibold text-[13px] text-ink/60 mb-2">История пополнений дней</div>
        <div className="flex flex-col gap-2">
          {daysHistory.map((h) => (
            <div key={h.id} className="flex items-center gap-2.5 bg-app-card border border-white/[.06] rounded-[14px] px-3.5 py-2.5">
              <div className="w-8 h-8 rounded-[10px] bg-gold/10 flex items-center justify-center flex-shrink-0">
                {HISTORY_ICON[h.type]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-[13px] text-ink truncate">{h.label}</div>
                <div className="font-medium text-[11px] text-ink/40">{h.date}</div>
              </div>
              <span className="font-display font-bold text-[13px] text-success whitespace-nowrap">+{h.days} дней</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
