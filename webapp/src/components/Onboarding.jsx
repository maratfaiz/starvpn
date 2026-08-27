import { useState } from "react";

const STORAGE_KEY = "star_vpn_ob";

const SLIDES = [
  {
    badge: "01 / 03",
    title: "Полная\nанонимность",
    sub: "Твой трафик зашифрован. Никаких логов, никакой слежки — мы не знаем кто ты.",
    icon: (
      <svg viewBox="0 0 56 56" width="52" height="52" fill="none" stroke="#FFB800" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M28 6L8 14v14c0 13 9 22 20 25 11-3 20-12 20-25V14z" />
        <circle cx="28" cy="26" r="7" />
        <line x1="28" y1="33" x2="28" y2="40" />
        <line x1="23" y1="40" x2="33" y2="40" />
      </svg>
    ),
  },
  {
    badge: "02 / 03",
    title: "Молниеносная\nскорость",
    sub: "Протокол VLESS + Reality — обходит блокировки и работает быстрее обычного VPN.",
    icon: (
      <svg viewBox="0 0 56 56" width="52" height="52" fill="none" stroke="#FFB800" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M30 8L10 30h18l-2 18 20-24H28z" />
      </svg>
    ),
  },
  {
    badge: "03 / 03",
    title: "Интернет\nбез границ",
    sub: "Любые сайты, сервисы и страны. Блокировки не существует — ты везде дома.",
    icon: (
      <svg viewBox="0 0 56 56" width="52" height="52" fill="none" stroke="#FFB800" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="28" cy="28" r="20" />
        <line x1="8" y1="28" x2="48" y2="28" />
        <path d="M28 8a30 30 0 010 40M28 8a30 30 0 000 40" />
      </svg>
    ),
  },
];

const PERKS = [
  { title: "Защита от слежки", sub: "Шифрование трафика · Нет логов" },
  { title: "Максимальная скорость", sub: "VLESS + Reality · Нидерланды" },
  { title: "До 3 устройств", sub: "iOS · Android · macOS · Windows" },
];

export function onboardingSeen() {
  try {
    return !!localStorage.getItem(STORAGE_KEY);
  } catch {
    return false;
  }
}

export default function Onboarding({ trialUsed, onFinish }) {
  const [slide, setSlide] = useState(0);
  const total = SLIDES.length + 1;
  const isFinal = slide === total - 1;

  const finish = (action) => {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* private mode etc. */
    }
    onFinish(action);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-app-bg flex flex-col overflow-hidden">
      {!isFinal && (
        <button onClick={() => setSlide(total - 1)} className="absolute top-4 right-4 z-10 text-[13px] font-medium text-ink/40">
          Пропустить
        </button>
      )}

      <div
        className="flex flex-1"
        style={{ transform: `translateX(-${(slide / total) * 100}%)`, transition: "transform .35s cubic-bezier(.32,.72,0,1)", width: `${total * 100}%` }}
      >
        {SLIDES.map((s) => (
          <div key={s.badge} className="w-full flex-shrink-0 flex flex-col items-center justify-center px-8 text-center" style={{ width: `${100 / total}%` }}>
            <div className="relative w-36 h-36 rounded-full flex items-center justify-center mb-10 bg-gold/10 border border-gold/25 shadow-[0_0_60px_rgba(255,184,0,.2)]">
              {s.icon}
            </div>
            <div className="font-display font-semibold text-[11px] text-gold tracking-widest mb-3">{s.badge}</div>
            <div className="font-display font-extrabold text-[28px] text-ink leading-tight whitespace-pre-line">{s.title}</div>
            <div className="font-medium text-sm text-ink/50 mt-3 max-w-[280px] leading-relaxed">{s.sub}</div>
          </div>
        ))}

        <div className="w-full flex-shrink-0 flex flex-col items-center justify-center px-8 text-center pb-8" style={{ width: `${100 / total}%` }}>
          <div className="w-14 h-14 rounded-2xl bg-gold/10 border border-gold/25 flex items-center justify-center mb-4">
            <svg viewBox="0 0 40 40" width="26" height="26" fill="none" stroke="#FFB800" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 4L6 9v10c0 9 6.5 16 14 18 7.5-2 14-9 14-18V9z" />
              <path d="M14 19l4 4 8-8" />
            </svg>
          </div>
          <div className="font-display font-extrabold text-2xl text-ink">Начнём?</div>
          <div className="font-medium text-sm text-ink/50 mt-2">Выбери тариф или попробуй 2 дня бесплатно</div>

          <div className="flex flex-col gap-2.5 w-full mt-7">
            {PERKS.map((p) => (
              <div key={p.title} className="flex items-center gap-3 bg-app-card border border-white/[.06] rounded-2xl px-3.5 py-3 text-left">
                <div className="w-9 h-9 rounded-[10px] bg-gold/10 flex items-center justify-center flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-gold" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[13px] text-ink">{p.title}</div>
                  <div className="font-medium text-[11px] text-ink/40">{p.sub}</div>
                </div>
                <div className="w-5 h-5 rounded-full bg-success/[.15] flex items-center justify-center flex-shrink-0">
                  <svg viewBox="0 0 10 10" width="9" height="9" fill="none" stroke="#4ADE80" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="1.5 5 4 7.5 8.5 2.5" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="px-6 flex-shrink-0" style={{ paddingBottom: "calc(28px + env(safe-area-inset-bottom, 0px))" }}>
        {!isFinal && (
          <div className="flex justify-center gap-1.5 mb-5">
            {SLIDES.map((_, i) => (
              <div key={i} className="h-1.5 rounded-full transition-all" style={{ width: i === slide ? 20 : 6, background: i === slide ? "#FFB800" : "rgba(255,255,255,.15)" }} />
            ))}
          </div>
        )}

        {!isFinal ? (
          <>
            <button
              onClick={() => setSlide((s) => Math.min(s + 1, total - 1))}
              className="w-full py-4 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[15px] text-[#1A1408]"
            >
              {slide === SLIDES.length - 1 ? "Начать" : "Далее"}
            </button>
            {slide === 0 && <div className="text-center font-medium text-xs text-ink/30 mt-3">Листай дальше чтобы узнать больше</div>}
          </>
        ) : (
          <div className="flex flex-col gap-2.5">
            <button
              onClick={() => finish("buy")}
              className="w-full py-4 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[15px] text-[#1A1408]"
            >
              Купить подписку
            </button>
            {!trialUsed ? (
              <button onClick={() => finish("trial")} className="w-full py-4 rounded-2xl border border-gold/35 bg-gold/[.08] font-display font-bold text-[15px] text-gold">
                Попробовать 2 дня бесплатно
              </button>
            ) : (
              <button onClick={() => finish("skip")} className="w-full py-4 rounded-2xl border border-white/10 font-display font-bold text-[15px] text-ink/60">
                Продолжить без подписки
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
