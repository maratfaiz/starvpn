import { DeviceIcon, ChevronIcon } from "../components/icons.jsx";

const ICON_SHAPE = { ios: "phone", android: "phone", macos: "laptop", windows: "laptop" };

function fmtGB(n) {
  return n >= 1 ? n.toFixed(2) + " ГБ" : (n * 1024).toFixed(0) + " МБ";
}

export default function DevicesScreen({ devices, devicesLimit, totalTrafficGb, onOpenDevice, onAddDevice }) {
  const full = devices.length >= devicesLimit;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="font-display font-extrabold text-[22px] text-ink">Устройства</div>
        <div className="font-medium text-[13px] text-ink/45 mt-0.5">
          {devices.length} из {devicesLimit} устройств подключено
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2.5">
          <span className="font-semibold text-[13px] text-ink/55">Использование трафика</span>
          <span className="font-medium text-[11px] text-ink/35">За всё время</span>
        </div>
        <div className="bg-app-card border border-white/[.06] rounded-[18px] p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-[11px] text-ink/45">Всего по всем устройствам</span>
            <div className="w-6 h-6 rounded-lg bg-gold/[.12] flex items-center justify-center">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#F7CE68" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 22s8-7.5 8-13a8 8 0 10-16 0c0 5.5 8 13 8 13z" />
                <circle cx="12" cy="9" r="2.5" />
              </svg>
            </div>
          </div>
          <div className="font-display font-extrabold text-lg text-ink">{fmtGB(totalTrafficGb)}</div>
        </div>
      </div>

      <div className="flex flex-col gap-2.5">
        {devices.map((d) => (
          <button
            key={d.id}
            onClick={() => onOpenDevice(d.id)}
            className="bg-app-card border border-white/[.06] rounded-2xl p-3.5 flex items-center gap-3 text-left"
          >
            <div className="w-10 h-10 rounded-[11px] bg-white/[.05] flex items-center justify-center flex-shrink-0">
              <DeviceIcon type={ICON_SHAPE[d.type] || "phone"} />
            </div>
            <div className="flex-1 min-w-0">
              <span className="font-semibold text-[13.5px] text-ink truncate block">{d.name}</span>
              <div className="font-medium text-[11.5px] text-ink/40 mt-0.5">
                {d.last_online} · {d.traffic_gb.toFixed(2)} ГБ
              </div>
            </div>
            <ChevronIcon />
          </button>
        ))}
      </div>

      {!full && (
        <button
          onClick={onAddDevice}
          className="border-[1.5px] border-dashed border-gold/40 py-3.5 rounded-2xl bg-gold/[.06] flex items-center justify-center gap-2"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F7CE68" strokeWidth="2.4">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span className="font-display font-bold text-[13.5px] text-gold">Добавить устройство</span>
        </button>
      )}
    </div>
  );
}
