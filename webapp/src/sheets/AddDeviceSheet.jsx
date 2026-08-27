import { useState } from "react";
import BottomSheet from "../components/BottomSheet.jsx";
import { DeviceIcon } from "../components/icons.jsx";

const TYPES = [
  { type: "ios", label: "iPhone / iPad", deviceIcon: "phone" },
  { type: "android", label: "Android", deviceIcon: "phone" },
  { type: "macos", label: "macOS", deviceIcon: "laptop" },
  { type: "windows", label: "Windows", deviceIcon: "laptop" },
];

export default function AddDeviceSheet({ open, onClose, onSubmit, submitting }) {
  const [type, setType] = useState("ios");

  const handleSubmit = () => {
    const picked = TYPES.find((t) => t.type === type);
    onSubmit(type, picked.label);
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Новое устройство" maxHeight="70%">
      <div className="font-medium text-[12.5px] text-ink/55 mb-3">Выбери тип устройства</div>
      <div className="grid grid-cols-2 gap-2.5 mb-5">
        {TYPES.map((t) => {
          const selected = t.type === type;
          return (
            <button
              key={t.type}
              onClick={() => setType(t.type)}
              className="flex flex-col items-center gap-2 py-4 rounded-2xl"
              style={{
                background: selected ? "rgba(255,184,0,.1)" : "#0D0C0A",
                border: `1.5px solid ${selected ? "rgba(255,184,0,.5)" : "rgba(255,255,255,.06)"}`,
              }}
            >
              <DeviceIcon type={t.deviceIcon} size={22} color={selected ? "#FFB800" : "#EBE0CC"} />
              <span className="font-display font-semibold text-[12.5px]" style={{ color: selected ? "#FFB800" : "#EBE0CC" }}>
                {t.label}
              </span>
            </button>
          );
        })}
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="w-full py-4 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[15px] text-[#1A1408] disabled:opacity-60"
      >
        {submitting ? "Создаём ключ…" : "Подключить устройство"}
      </button>
    </BottomSheet>
  );
}
