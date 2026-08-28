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
        className="fixed left-0 right-0 bottom-0 z-50 bg-app-sheet border-t border-gold/25 rounded-t-3xl px-5 pt-2.5 overflow-y-auto"
        style={{
          maxHeight,
          paddingBottom: "calc(26px + env(safe-area-inset-bottom, 0px))",
          transform: open ? "translateY(0)" : "translateY(100%)",
          transition: "transform .3s cubic-bezier(.32,.72,0,1)",
          // Тень только у поднятой шторки. Закрытая панель остаётся в DOM
          // (иначе не проиграть анимацию закрытия) и стоит вплотную к нижней
          // кромке экрана, а тень «0 -20px 50px» бьёт вверх — все восемь
          // шторок вместе затемняли полосу над таб-баром до чёрного.
          boxShadow: open ? "0 -20px 50px rgba(0,0,0,.5)" : "none",
        }}
      >
        <div className="w-9 h-1 rounded-full bg-white/15 mx-auto mb-4" />
        {title && (
          <div className="flex items-center justify-between mb-4">
            <span className="font-display font-extrabold text-base text-ink">{title}</span>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full bg-white/[.06] flex items-center justify-center"
              aria-label="Закрыть"
            >
              <CloseIcon />
            </button>
          </div>
        )}
        {children}
      </div>
    </>
  );
}
