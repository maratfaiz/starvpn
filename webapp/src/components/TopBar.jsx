/**
 * Узкая шапка приложения. В Telegram над ней стоит собственный заголовок
 * мессенджера, поэтому полоса намеренно низкая — она только называет
 * сервис, как строка «STAR VPN» в шапке сайта.
 */
export default function TopBar() {
  return (
    <div className="flex-shrink-0 flex items-center gap-2 px-5 h-11 bg-app-bg border-b border-white/[.06]">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="#FFB800" aria-hidden="true">
        <path d="M12 2.6l2.5 6.1 6.6.5-5 4.3 1.5 6.4L12 16.5 6.4 19.9l1.5-6.4-5-4.3 6.6-.5z" />
      </svg>
      <span className="font-display font-bold text-[14px] tracking-[.05em] text-gold">
        STAR VPN
      </span>
    </div>
  );
}
