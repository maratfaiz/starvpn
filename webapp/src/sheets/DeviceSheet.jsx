import { useEffect, useState } from "react";
import BottomSheet from "../components/BottomSheet.jsx";
import { DeviceIcon } from "../components/icons.jsx";

const STATUS_COLOR = {
  Онлайн: "#4ADE80",
};

const ROWS = [
  ["Статус", (d) => d.status_label, (d) => STATUS_COLOR[d.status_label] || "rgba(235,224,204,.4)"],
  ["Трафик", (d) => `${d.traffic_gb.toFixed(2)} ГБ`],
  ["Последняя активность", (d) => d.last_online],
  ["Слот", (d) => d.slot],
  [
    "Добавлено",
    (d) =>
      new Date(d.created_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "2-digit" }),
  ],
];

export default function DeviceSheet({ open, device, onClose, onDelete, onShowLink, onShowSubscription }) {
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (!open) setConfirming(false);
  }, [open, device?.id]);

  if (!device) return <BottomSheet open={false} onClose={onClose} maxHeight="80%" />;

  if (confirming) {
    return (
      <BottomSheet open={open} onClose={onClose} title="Удалить устройство?" maxHeight="50%">
        <p className="font-medium text-[13.5px] text-ink/60 leading-relaxed mb-5">
          Удалить «{device.name}»? VPN-доступ будет отключён.
        </p>
        <div className="flex gap-2.5">
          <button
            onClick={() => setConfirming(false)}
            className="flex-1 py-3.5 rounded-[14px] border border-white/10 font-display font-bold text-[13.5px] text-ink/70"
          >
            Отмена
          </button>
          <button
            onClick={() => onDelete(device.id)}
            className="flex-1 py-3.5 rounded-[14px] border border-danger/35 bg-danger/[.1] font-display font-bold text-[13.5px] text-danger"
          >
            Удалить
          </button>
        </div>
      </BottomSheet>
    );
  }

  return (
    <BottomSheet open={open} onClose={onClose} maxHeight="80%">
      <div className="flex items-center gap-2.5 mb-[18px] -mt-1">
        <div className="w-[38px] h-[38px] rounded-[11px] bg-white/[.05] flex items-center justify-center">
          <DeviceIcon type={device.type} />
        </div>
        <span className="font-display font-extrabold text-base text-ink">{device.name}</span>
      </div>

      <div className="bg-app-card border border-white/[.06] rounded-2xl overflow-hidden mb-3.5">
        {ROWS.map(([label, getValue, getColor], i) => (
          <div
            key={label}
            className={`flex justify-between px-3.5 py-3 ${i < ROWS.length - 1 ? "border-b border-white/[.05]" : ""}`}
          >
            <span className="font-medium text-[12.5px] text-ink/45">{label}</span>
            <span className="font-semibold text-[12.5px]" style={{ color: getColor ? getColor(device) : "#EBE0CC" }}>
              {getValue(device)}
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2.5">
        <div className="flex gap-2.5">
          <button
            onClick={() => onShowLink(device)}
            className="flex-1 border border-gold/35 bg-gold/[.08] py-3.5 rounded-[14px] font-display font-bold text-[13.5px] text-gold"
          >
            🔑 Ключ
          </button>
          <button
            onClick={() => onShowSubscription(device)}
            className="flex-1 border border-gold/35 bg-gold/[.08] py-3.5 rounded-[14px] font-display font-bold text-[13.5px] text-gold"
          >
            🔗 Ссылка
          </button>
        </div>
        <button
          onClick={() => setConfirming(true)}
          className="w-full border border-danger/35 bg-danger/[.08] py-3.5 rounded-[14px] font-display font-bold text-[13.5px] text-danger"
        >
          Удалить устройство
        </button>
      </div>
    </BottomSheet>
  );
}
