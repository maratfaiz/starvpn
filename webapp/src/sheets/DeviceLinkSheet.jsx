import { useEffect, useState } from "react";
import QRCode from "qrcode";
import BottomSheet from "../components/BottomSheet.jsx";

export default function DeviceLinkSheet({ open, deviceName, link, subUrl, onClose, onCopy, onCopySub }) {
  const [qrDataUrl, setQrDataUrl] = useState(null);

  useEffect(() => {
    if (!open || !link) {
      setQrDataUrl(null);
      return;
    }
    let cancelled = false;
    QRCode.toDataURL(link, { width: 240, margin: 1, color: { dark: "#0A0D13", light: "#F7CE68" } })
      .then((url) => {
        if (!cancelled) setQrDataUrl(url);
      })
      .catch(() => setQrDataUrl(null));
    return () => {
      cancelled = true;
    };
  }, [open, link]);

  return (
    <BottomSheet open={open} onClose={onClose} title={deviceName || "Ключ доступа"} maxHeight="88%">
      <div className="flex flex-col items-center">
        <div className="w-[240px] h-[240px] rounded-2xl bg-white/[.03] border border-white/[.06] flex items-center justify-center overflow-hidden mb-4">
          {qrDataUrl ? (
            <img src={qrDataUrl} alt="QR-код VLESS ключа" className="w-full h-full object-contain" />
          ) : (
            <div className="w-6 h-6 rounded-full border-2 border-gold/30 border-t-gold animate-spin" />
          )}
        </div>

        <div className="w-full bg-app-card border border-white/[.06] rounded-[14px] px-3.5 py-3 mb-3">
          <div className="font-mono text-[11px] text-ink/60 break-all leading-relaxed">{link}</div>
        </div>

        <button
          onClick={onCopy}
          className="w-full py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[14px] text-[#1A1408]"
        >
          Скопировать ссылку
        </button>
        <div className="text-center font-medium text-[11.5px] text-ink/30 mt-3">
          Отсканируй QR или вставь ссылку в приложение VPN-клиента
        </div>

        {subUrl && (
          <div className="w-full mt-5 pt-5 border-t border-white/[.06]">
            <div className="font-semibold text-[12.5px] text-ink/55 mb-2">Используешь Happ?</div>
            <div className="font-medium text-[11.5px] text-ink/40 mb-3 leading-relaxed">
              Добавь эту ссылку как <b className="text-ink/60">подписку</b> (Subscription), а не отдельный конфиг —
              приложение покажет «STAR VPN» вместо технического имени и само предупредит,
              когда подписка закончится.
            </div>
            <div className="w-full bg-app-card border border-white/[.06] rounded-[14px] px-3.5 py-3 mb-3">
              <div className="font-mono text-[11px] text-ink/60 break-all leading-relaxed">{subUrl}</div>
            </div>
            <button
              onClick={onCopySub}
              className="w-full py-3 rounded-2xl border border-gold/35 bg-gold/[.08] font-display font-bold text-[13px] text-gold"
            >
              Скопировать ссылку подписки
            </button>
          </div>
        )}
      </div>
    </BottomSheet>
  );
}
