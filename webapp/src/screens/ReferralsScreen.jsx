import { StarIcon, ShareIcon } from "../components/icons.jsx";

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

const STEPS = (referral) => [
  { title: "Отправь ссылку", text: "Друг переходит по твоей ссылке." },
  { title: `Друг оформляет подписку`, text: `Сразу получает +${referral.refereeBonusDays} дня.` },
  { title: `Друг остаётся ${referral.vestingDays} дней`, text: "Это защита от возвратов и чарджбэков." },
  { title: `Получаешь +${referral.daysPerReferral} дней`, text: "Дни автоматически добавляются к твоей подписке." },
];

export default function ReferralsScreen({ referral, daysHistory, copied, onCopyCode, onShare }) {
  return (
    <div className="flex flex-col gap-3.5">
      <div className="font-display font-extrabold text-[22px] text-ink">Реферальная программа</div>

      {/* hero */}
      <div className="relative rounded-3xl p-[22px] overflow-hidden border border-gold/30 bg-[linear-gradient(160deg,#120E06_0%,#0C0E12_60%)]">
        <StarIcon size={10} className="absolute top-4 right-5 animate-[starTwinkle_2.4s_ease-in-out_infinite]" />
        <div className="font-medium text-[13px] text-ink/55">Пригласи друга — получи</div>
        <div className="flex items-end gap-2 mt-1">
          <span className="font-display font-extrabold text-[40px] leading-none text-gold">
            +{referral.daysPerReferral}
          </span>
          <span className="font-semibold text-[15px] text-ink/70 pb-1">дней</span>
        </div>
        <div className="font-medium text-[12.5px] text-ink/45 mt-2.5 leading-relaxed max-w-[280px]">
          Друг оформляет подписку по твоей ссылке — сразу получает +{referral.refereeBonusDays} дня, а ты
          получаешь +{referral.daysPerReferral} дней, когда он остаётся активным {referral.vestingDays} дней.
        </div>
      </div>

      {/* link */}
      <div className="bg-app-card border border-white/[.06] rounded-[18px] p-4">
        <div className="mb-3">
          <span className="font-display font-semibold text-[11px] text-ink/40 tracking-widest uppercase">
            Твоя ссылка
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
        <div className="font-medium text-[11.5px] text-ink/40 mt-2.5">
          Другу — +{referral.refereeBonusDays} дня, тебе — +{referral.daysPerReferral} дней
        </div>
      </div>

      {/* stats */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 text-center">
          <div className="font-display font-extrabold text-[20px] text-ink">{referral.invitedCount}</div>
          <div className="font-medium text-[11px] text-ink/40 mt-1">Приглашённых</div>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-2xl py-3.5 text-center">
          <div className="font-display font-extrabold text-[20px] text-gold">{referral.daysEarned}</div>
          <div className="font-medium text-[11px] text-ink/40 mt-1">Дней получено</div>
        </div>
      </div>

      <button
        onClick={onShare}
        className="border-none py-[15px] rounded-[18px] bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2"
      >
        <ShareIcon />
        <span className="font-display font-bold text-[14.5px] text-[#1A1408]">Поделиться ссылкой</span>
      </button>

      {/* how it works */}
      <div className="bg-app-card border border-white/[.06] rounded-2xl px-4 py-3.5">
        <div className="font-semibold text-[13px] text-ink/60 mb-3">Как это работает</div>
        <div className="flex flex-col gap-3">
          {STEPS(referral).map((step, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-gold/10 border border-gold/30 flex items-center justify-center flex-shrink-0">
                <span className="font-display font-bold text-[11px] text-gold">{i + 1}</span>
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-[12.5px] text-ink">{step.title}</div>
                <div className="font-medium text-[11.5px] text-ink/45 mt-0.5 leading-snug">{step.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* limit */}
      <div className="rounded-2xl border border-white/[.06] bg-app-card px-4 py-3 flex items-start gap-2.5">
        <div className="mt-0.5 flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(245,243,238,.35)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 9v4M12 17h.01M10.3 3.9L2.7 17.5a1.8 1.8 0 001.6 2.7h15.4a1.8 1.8 0 001.6-2.7L13.7 3.9a1.8 1.8 0 00-3.4 0z" />
          </svg>
        </div>
        <div>
          <div className="font-semibold text-[12.5px] text-ink/70">
            Лимит: {referral.monthlyCapDays} бонусных дней в месяц
          </div>
          <div className="font-medium text-[11px] text-ink/40 mt-0.5">
            Максимум {referral.monthlyCapReferrals} успешных приглашений по +{referral.daysPerReferral} дней.
          </div>
        </div>
      </div>

      {/* history */}
      <div>
        <div className="font-semibold text-[13px] text-ink/60 mb-2">История бонусов</div>
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
