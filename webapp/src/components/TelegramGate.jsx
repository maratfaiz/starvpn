export default function TelegramGate() {
  return (
    <div className="fixed inset-0 z-[100] bg-app-bg flex flex-col items-center justify-center text-center px-8">
      <div className="relative w-24 h-24 rounded-full bg-gold/10 border border-gold/25 flex items-center justify-center mb-6">
        <div className="absolute inset-0 rounded-full border border-gold/20 animate-ping" />
        <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="#FFB800" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </div>
      <div className="font-display font-extrabold text-xl text-ink">Открой в Telegram</div>
      <div className="font-medium text-sm text-ink/45 mt-2 max-w-[260px]">
        Это приложение работает только внутри Telegram
      </div>
      <a href="https://t.me/starisvpnbot" className="w-full max-w-[280px] mt-7">
        <button className="w-full py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center gap-2">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#1A1408" strokeWidth="2.5" strokeLinecap="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          <span className="font-display font-bold text-[14px] text-[#1A1408]">Открыть бота</span>
        </button>
      </a>
    </div>
  );
}
