import BottomSheet from "../components/BottomSheet.jsx";

export default function SubscriptionLinkSheet({ open, deviceName, subUrl, onClose, onCopy }) {
  return (
    <BottomSheet open={open} onClose={onClose} title={deviceName || "Ссылка-подписка"} maxHeight="60%">
      <div className="flex flex-col items-center">
        <div className="font-medium text-[12.5px] text-ink/45 mb-4 leading-relaxed text-center">
          Открой в Happ, v2rayNG или другом клиенте — сервер добавится автоматически
          под именем «STAR VPN» и сам предупредит, когда подписка закончится.
        </div>

        <div className="w-full bg-app-card border border-white/[.06] rounded-[14px] px-3.5 py-3 mb-3">
          <div className="font-mono text-[11px] text-ink/60 break-all leading-relaxed">{subUrl}</div>
        </div>

        <button
          onClick={onCopy}
          className="w-full py-3.5 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[14px] text-[#1A1408]"
        >
          Скопировать ссылку
        </button>
      </div>
    </BottomSheet>
  );
}
