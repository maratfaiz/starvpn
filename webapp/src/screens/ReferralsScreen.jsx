import { StarIcon, ShareIcon } from "../components/icons.jsx";

export default function ReferralsScreen({ referral, copied, onCopyCode, onShare }) {
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

      <div className="grid grid-cols-2 gap-2.5">
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 px-2 text-center">
          <div className="font-display font-extrabold text-[19px] text-ink">{referral.paidCount}</div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-1">оплатили</div>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 px-2 text-center">
          <div className="font-display font-extrabold text-[19px] text-gold">{referral.daysEarned}</div>
          <div className="font-medium text-[10.5px] text-ink/40 mt-1">дней получено</div>
        </div>
      </div>

      <div className="bg-app-card border border-white/[.06] rounded-2xl px-4 py-3.5">
        <div className="font-semibold text-[13px] text-ink/60 mb-1">Как начисляется</div>
        <div className="font-medium text-[12.5px] text-ink/50 leading-relaxed mb-2.5">
          За каждые {referral.milestoneSize} друзей, оформивших подписку, — автоматически
          +{referral.bonusDays} дней к твоей подписке. Без баланса и вывода.
        </div>
        <div className="flex items-center gap-2.5">
          <div className="flex-1 h-1.5 rounded-full bg-white/[.06] overflow-hidden">
            <div
              className="h-full rounded-full bg-gold"
              style={{ width: `${((referral.paidCount % referral.milestoneSize) / referral.milestoneSize) * 100}%` }}
            />
          </div>
          <span className="font-display font-semibold text-[11px] text-ink/45 flex-shrink-0">
            {referral.paidCount % referral.milestoneSize} / {referral.milestoneSize}
          </span>
        </div>
      </div>

      <div>
        <div className="font-semibold text-[13px] text-ink/60 mb-2">Достижения</div>
        <div className="grid grid-cols-2 gap-2.5">
          {referral.achievements.map((a) => (
            <div
              key={a.key}
              className={`rounded-2xl px-3 py-3.5 text-center border ${
                a.unlocked ? "bg-gold/[.08] border-gold/35" : "bg-app-card border-white/[.06]"
              }`}
            >
              <div className={`text-2xl mb-1.5 ${a.unlocked ? "" : "grayscale opacity-40"}`}>{a.icon}</div>
              <div className={`font-display font-bold text-[12px] ${a.unlocked ? "text-gold" : "text-ink/50"}`}>
                {a.title}
              </div>
              <div className="font-medium text-[10.5px] text-ink/35 mt-0.5">
                {a.unlocked ? `+${a.bonusDays} дней получено ✅` : `${a.threshold} друзей · +${a.bonusDays} дней`}
              </div>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={onShare}
        className="border-none py-[15px] rounded-[18px] bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
      >
        <ShareIcon />
        <span className="font-display font-bold text-[14.5px] text-[#1A1408]">Поделиться ссылкой</span>
      </button>
    </div>
  );
}
