import { CloseIcon } from "./icons.jsx";

/**
 * Generic slide-up bottom sheet: dimmed backdrop + panel sliding from
 * the bottom. `open` controls both the transform and pointer-events so
 * the close transition can play out.
 */
export default function BottomSheet({ open, onClose, title, maxHeight = "80%", children }) {
  return (
    <>
      <div
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/60 transition-opacity duration-200"
        style={{ opacity: open ? 1 : 0, pointerEvents: open ? "auto" : "none" }}
      />
      <div
        className="fixed left-0 right-0 bottom-0 z-50 bg-app-sheet border-t border-gold/25 rounded-t-3xl px-5 pt-4 shadow-sheet overflow-y-auto"
        style={{
          maxHeight,
          paddingBottom: "calc(26px + env(safe-area-inset-bottom, 0px))",
          transform: open ? "translateY(0)" : "translateY(100%)",
          transition: "transform .3s cubic-bezier(.32,.72,0,1)",
        }}
      >
        <button
          onClick={onClose}
          className="absolute top-3.5 right-4 w-7 h-7 rounded-full bg-white/[.06] flex items-center justify-center z-[1]"
          aria-label="Закрыть"
        >
          <CloseIcon />
        </button>
        {title && (
          <div className="mb-4 pr-9">
            <span className="font-display font-extrabold text-base text-ink">{title}</span>
          </div>
        )}
        {children}
      </div>
    </>
  );
}
