export default function Toast({ message }) {
  return (
    <div
      className="fixed left-1/2 -translate-x-1/2 z-[60] bg-[rgba(10,8,0,.96)] border border-gold/25 rounded-2xl px-4 py-2.5 font-display font-medium text-[13px] text-ink text-center transition-all duration-200"
      style={{
        bottom: "calc(72px + env(safe-area-inset-bottom, 0px) + 16px)",
        opacity: message ? 1 : 0,
        transform: message ? "translate(-50%, 0)" : "translate(-50%, 8px)",
        pointerEvents: "none",
        maxWidth: "calc(100vw - 32px)",
        width: "max-content",
      }}
    >
      {message}
    </div>
  );
}
