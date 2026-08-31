import { StarIcon, ShareIcon, MedalIcon, DiamondIcon, UsersIcon } from "../components/icons.jsx";

function pluralFriends(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "друзей";
  if (mod10 === 1) return "друг";
  if (mod10 >= 2 && mod10 <= 4) return "друга";
  return "друзей";
}

function achievementIcon(icon, size) {
  switch (icon) {
    case "bronze":
      return <MedalIcon size={size} color="#CD7F32" />;
    case "silver":
      return <MedalIcon size={size} color="#C0C0C0" />;
    case "gold":
      return <MedalIcon size={size} color="#FFD700" />;
    case "diamond":
      return <DiamondIcon size={size} color="#7DD3FC" />;
    default:
      return null;
  }
}

const HISTORY_ICON = {
  referral: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFB800" strokeWidth="2">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.5 19c0-3.2 2.9-5.5 6.5-5.5s6.5 2.3 6.5 5.5" />
    </svg>
  ),
  bonus: <StarIcon size={14} />,
  purchase: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFB800" strokeWidth="2">
      <path d="M13 2L3 14h7l-1 8 11-13h-7l1-7z" />
    </svg>
  ),
};

export default function ReferralsScreen({ referral, daysHistory, copied, onCopyCode, onShare }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="relative rounded-3xl p-[22px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#120E06_0%,#0C0E12_60%)]">
        <StarIcon size={10} className="absolute top-4 right-5 animate-[starTwinkle_2.4s_ease-in-out_infinite]" />
        <div className="font-display font-extrabold text-[19px] text-ink leading-tight max-w-[230px]">
          Приглашайте друзей — получайте дни VPN бесплатно
        </div>
        <div className="font-medium text-[13px] text-ink/50 mt-2">
          +{referral.daysPerReferral} дней за каждого друга, который оплатит подписку и останется с нами {referral.vestingDays} дней
        </div>
      </div>

      {/* link + stats, merged into one section */}
      <div className="bg-app-card border border-white/[.06] rounded-[18px] p-4">
        <div className="mb-3">
          <span className="font-display font-semibold text-[11px] text-ink/40 tracking-widest uppercase">
            Ваша ссылка
          </span>
        </div>

        <div className="flex items-center gap-2 bg-white/[.05] border border-white/[.08] rounded-[14px] px-3.5 py-3">
          <span className="flex-1 font-bold text-[15px] text-gold tracking-wider font-mono">{referral.code}</span>
          <button
            onClick={onCopyCode}
            className="font-display font-semibold text-xs text-[#1A1408] bg-gold px-3 py-1.5 rounded-[10px]"
          >
            {copied ? "Скопировано" : "Копировать"}
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2.5 mt-4 pt-4 border-t border-white/[.06]">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-[12px] text-ink/50">Приглашено</span>
              <UsersIcon size={15} color="rgba(245,243,238,.35)" />
            </div>
            <div className="font-display font-extrabold text-lg text-ink">{referral.invitedCount}</div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-[12px] text-ink/50">Дней получено</span>
              <StarIcon size={15} />
            </div>
            <div className="font-display font-extrabold text-lg text-gold">{referral.daysEarned}</div>
          </div>
        </div>
      </div>

      <div className="bg-app-card border border-white/[.06] rounded-2xl px-4 py-3.5">
        <div className="font-semibold text-[13px] text-ink/60 mb-3">Как это работает</div>
        <div className="flex flex-col gap-3">
          {[
            "Друг переходит по вашей ссылке и оформляет платную подписку",
            `Остаётся активным подписчиком ${referral.vestingDays} дней подряд — это защита от возвратов`,
            `Вам автоматически начисляется +${referral.daysPerReferral} дней — без баланса и вывода, лимит ${referral.annualCapDays} в год`,
          ].map((step, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-gold/10 border border-gold/30 flex items-center justify-center flex-shrink-0">
                <span className="font-display font-bold text-[11px] text-gold">{i + 1}</span>
              </div>
              <div className="font-medium text-[12.5px] text-ink/55 leading-snug pt-0.5">{step}</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="font-semibold text-[13px] text-ink/60 mb-2">Достижения</div>
        <div className="grid grid-cols-4 gap-2">
          {referral.achievements.map((a) => (
            <div
              key={a.key}
              className={`rounded-xl px-1.5 py-2.5 text-center border ${
                a.unlocked ? "bg-gold/[.08] border-gold/35" : "bg-app-card border-white/[.06]"
              }`}
            >
              <div className={`flex justify-center mb-1 ${a.unlocked ? "" : "grayscale opacity-40"}`}>
                {achievementIcon(a.icon, 18)}
              </div>
              <div className={`font-display font-bold text-[9.5px] leading-tight ${a.unlocked ? "text-gold" : "text-ink/50"}`}>
                {a.title}
              </div>
              <div className="font-medium text-[8.5px] text-ink/35 leading-tight">
                {a.threshold} {pluralFriends(a.threshold)}
              </div>
              <div className="font-semibold text-[8.5px] text-gold/70 leading-tight">
                +{a.threshold * referral.daysPerReferral} дней
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
