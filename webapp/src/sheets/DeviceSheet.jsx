import BottomSheet from "../components/BottomSheet.jsx";
import { DeviceIcon } from "../components/icons.jsx";

const ROWS = [
  ["Статус", (d) => d.statusText, (d) => d.statusColor],
  ["Трафик", (d) => `${d.traffic} ГБ`],
  ["Последняя активность", (d) => d.lastActive],
  ["Подключено с", (d) => d.connectedSince],
  ["Локация", (d) => d.location],
  ["IP-адрес", (d) => d.ip, null, true],
  ["Протокол", (d) => d.protocol],
];

export default function DeviceSheet({ open, device, onClose, onDelete }) {
  if (!device) return <BottomSheet open={false} onClose={onClose} maxHeight="80%" />;

  const statusText = device.current ? "Онлайн" : "Не в сети";
  const statusColor = device.current ? "#2ED9A6" : "rgba(245,243,238,.4)";
  const enriched = { ...device, statusText, statusColor };

  return (
    <BottomSheet open={open} onClose={onClose} maxHeight="80%">
      <div className="flex items-center gap-2.5 mb-[18px] -mt-1">
        <div className="w-[38px] h-[38px] rounded-[11px] bg-white/[.05] flex items-center justify-center">
          <DeviceIcon type={device.type} />
        </div>
        <span className="font-display font-extrabold text-base text-ink">{device.name}</span>
      </div>

      <div className="bg-app-card border border-white/[.06] rounded-2xl overflow-hidden mb-3.5">
        {ROWS.map(([label, getValue, getColor, mono], i) => (
          <div
            key={label}
            className={`flex justify-between px-3.5 py-3 ${i < ROWS.length - 1 ? "border-b border-white/[.05]" : ""}`}
          >
            <span className="font-medium text-[12.5px] text-ink/45">{label}</span>
            <span
              className={`font-semibold text-[12.5px] ${mono ? "font-mono" : ""}`}
              style={{ color: getColor ? getColor(enriched) : "#F5F3EE" }}
            >
              {getValue(enriched)}
            </span>
          </div>
        ))}
      </div>

      <button
        onClick={() => onDelete(device.id)}
        className="w-full border border-danger/35 bg-danger/[.08] py-3.5 rounded-[14px] font-display font-bold text-[13.5px] text-danger"
      >
        Удалить устройство
      </button>
    </BottomSheet>
  );
}
