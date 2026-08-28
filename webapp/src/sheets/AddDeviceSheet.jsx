import { useEffect, useState } from "react";
import BottomSheet from "../components/BottomSheet.jsx";
import { DeviceIcon } from "../components/icons.jsx";

/**
 * Добавление устройства в два шага.
 *
 * Шаг 1 — крупная категория: телефон, планшет, компьютер, телевизор.
 * Так же сгруппированы устройства в личном кабинете на сайте, и человеку
 * не нужно с порога вспоминать, какая у него операционная система.
 *
 * Шаг 2 — система внутри категории и название. Система всё равно нужна:
 * от неё зависит и ключ (POST /api/devices принимает ios / android /
 * macos / windows / linux / androidtv / appletv), и то, какое приложение
 * показать в инструкции. Название — новое: раньше устройство молча
 * называлось по системе, и три телефона в списке различить было нельзя.
 */

const CATEGORIES = [
  {
    id: "phone",
    label: "Телефон",
    icon: "phone",
    systems: [
      { type: "ios", label: "iPhone", suggest: "iPhone" },
      { type: "android", label: "Android", suggest: "Телефон Android" },
    ],
  },
  {
    id: "tablet",
    label: "Планшет",
    icon: "tablet",
    systems: [
      { type: "ios", label: "iPad", suggest: "iPad" },
      { type: "android", label: "Android", suggest: "Планшет Android" },
    ],
  },
  {
    id: "computer",
    label: "Компьютер",
    icon: "laptop",
    systems: [
      { type: "macos", label: "macOS", suggest: "Мой Mac" },
      { type: "windows", label: "Windows", suggest: "Компьютер" },
      { type: "linux", label: "Linux", suggest: "Linux" },
    ],
  },
  {
    id: "tv",
    label: "Телевизор",
    icon: "tv",
    systems: [
      { type: "appletv", label: "Apple TV", suggest: "Apple TV" },
      { type: "androidtv", label: "Смарт-ТВ", suggest: "Телевизор" },
    ],
  },
];

const NAME_MAX = 64; // столько же, сколько в колонке devices.name

export default function AddDeviceSheet({ open, onClose, onSubmit, submitting }) {
  const [category, setCategory] = useState(null);
  const [system, setSystem] = useState(null);
  const [name, setName] = useState("");

  // Каждое открытие начинается с чистого выбора.
  useEffect(() => {
    if (!open) return;
    setCategory(null);
    setSystem(null);
    setName("");
  }, [open]);

  const pickCategory = (cat) => {
    setCategory(cat);
    const first = cat.systems[0];
    setSystem(first);
    setName(first.suggest);
  };

  const pickSystem = (sys) => {
    // Название меняем только пока человек не правил его сам.
    const untouched = !name || category.systems.some((s) => s.suggest === name);
    setSystem(sys);
    if (untouched) setName(sys.suggest);
  };

  const submit = () => {
    const clean = name.trim().slice(0, NAME_MAX) || system.suggest;
    onSubmit(system.type, clean);
  };

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title={category ? category.label : "Новое устройство"}
      maxHeight="76%"
    >
      {!category ? (
        <>
          <div className="font-medium text-[12.5px] text-ink/55 mb-3">
            Что подключаем?
          </div>
          <div className="grid grid-cols-2 gap-2.5 pb-1">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => pickCategory(cat)}
                className="flex flex-col items-center gap-2.5 py-5 rounded-2xl bg-app-card border border-white/[.06] active:border-gold/50"
              >
                <DeviceIcon type={cat.icon} size={24} color="#FFB800" />
                <span className="font-display font-semibold text-[13px] text-ink">
                  {cat.label}
                </span>
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="font-medium text-[12.5px] text-ink/55 mb-2.5">Система</div>
          <div className="flex flex-wrap gap-2 mb-5">
            {category.systems.map((sys) => {
              const picked = sys.type === system?.type && sys.label === system?.label;
              return (
                <button
                  key={sys.label}
                  onClick={() => pickSystem(sys)}
                  className="px-4 py-2.5 rounded-xl font-display font-semibold text-[13px]"
                  style={{
                    background: picked ? "rgba(255,184,0,.12)" : "rgba(255,255,255,.04)",
                    border: `1.5px solid ${picked ? "rgba(255,184,0,.5)" : "rgba(255,255,255,.07)"}`,
                    color: picked ? "#FFB800" : "rgba(235,224,204,.6)",
                  }}
                >
                  {sys.label}
                </button>
              );
            })}
          </div>

          <div className="font-medium text-[12.5px] text-ink/55 mb-2.5">Название</div>
          <input
            type="text"
            value={name}
            maxLength={NAME_MAX}
            onChange={(e) => setName(e.target.value)}
            placeholder={system?.suggest}
            aria-label="Название устройства"
            className="w-full bg-app-card border border-white/10 rounded-[14px] px-4 py-3.5 font-semibold text-[14px] text-ink outline-none focus:border-gold/45 placeholder:text-ink/25"
          />
          <div className="font-medium text-[11px] text-ink/30 mt-2">
            Чтобы отличать устройства в списке — например «Телефон жены».
          </div>

          <div className="flex gap-2.5 mt-5">
            <button
              onClick={() => setCategory(null)}
              className="px-5 py-4 rounded-2xl bg-white/[.05] border border-white/[.08] font-display font-bold text-[14px] text-ink/70"
            >
              Назад
            </button>
            <button
              onClick={submit}
              disabled={submitting}
              className="flex-1 py-4 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-[15px] text-[#1A1408] disabled:opacity-60"
            >
              {submitting ? "Создаём ключ…" : "Подключить"}
            </button>
          </div>
        </>
      )}
    </BottomSheet>
  );
}
