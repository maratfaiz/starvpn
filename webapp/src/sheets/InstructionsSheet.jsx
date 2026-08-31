import { useState } from "react";
import BottomSheet from "../components/BottomSheet.jsx";

const PLATFORMS = [
  {
    id: "ios",
    label: "iPhone",
    app: "Streisand",
    store: "App Store",
    storeUrl: "https://apps.apple.com/app/id6446544843",
    steps: [
      <>Скачай приложение <b>Streisand</b> из App Store (кнопка ниже)</>,
      <>Перейди на вкладку <b>Устройства</b> в этом приложении и нажми на своё устройство</>,
      <>Нажми <b>«Показать QR-код и ссылку»</b> и скопируй ключ</>,
      <>В Streisand нажми <b>«+»</b> → <b>«Импорт из буфера обмена»</b> → вставь ключ</>,
      <>Нажми <b>Connect</b> — готово! VPN подключён 🚀</>,
    ],
  },
  {
    id: "android",
    label: "Android",
    app: "v2rayNG",
    store: "Google Play",
    storeUrl: "https://play.google.com/store/apps/details?id=com.v2ray.ang",
    steps: [
      <>Скачай приложение <b>v2rayNG</b> из Google Play (кнопка ниже)</>,
      <>Перейди на вкладку <b>Устройства</b> и нажми на своё устройство → <b>«Показать ключ»</b></>,
      <>Скопируй строку ключа (начинается на <b>vless://</b>)</>,
      <>В v2rayNG нажми <b>«+»</b> → <b>«Импорт из буфера обмена»</b></>,
      <>Нажми кнопку запуска (треугольник) — VPN активен 🟢</>,
    ],
  },
  {
    id: "windows",
    label: "Windows",
    app: "v2rayN",
    store: "GitHub",
    storeUrl: "https://github.com/2dust/v2rayN/releases/latest",
    steps: [
      <>Скачай <b>v2rayN</b> с GitHub (кнопка ниже) — файл v2rayN-windows-64.zip</>,
      <>Распакуй архив и запусти <b>v2rayN.exe</b></>,
      <>Перейди в раздел <b>Устройства</b>, нажми на устройство → скопируй ключ</>,
      <>В v2rayN: меню <b>«Servers»</b> → <b>«Import bulk URL from clipboard»</b></>,
      <>Выбери сервер → нажми <b>«Set as active»</b> → включи системный прокси</>,
    ],
  },
  {
    id: "mac",
    label: "macOS",
    app: "V2Box",
    store: "Mac App Store",
    storeUrl: "https://apps.apple.com/app/v2box-v2ray-client/id6446814690",
    steps: [
      <>Скачай <b>V2Box</b> из Mac App Store (кнопка ниже)</>,
      <>Перейди в раздел <b>Устройства</b>, нажми на устройство → <b>«Показать ключ»</b></>,
      <>Скопируй строку ключа (начинается на <b>vless://</b>)</>,
      <>В V2Box нажми <b>«+»</b> → <b>«Import from clipboard»</b> → вставь ключ</>,
      <>Нажми <b>Connect</b> — VPN активен 🚀</>,
    ],
  },
];

export default function InstructionsSheet({ open, onClose }) {
  const [tab, setTab] = useState("ios");
  const platform = PLATFORMS.find((p) => p.id === tab);
  const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;

  return (
    <BottomSheet open={open} onClose={onClose} title="Подключение" maxHeight="85%">
      <div className="font-medium text-[12.5px] text-ink/45 -mt-2 mb-4">Выбери своё устройство и следуй инструкции</div>

      <div className="flex gap-1.5 mb-4 overflow-x-auto">
        {PLATFORMS.map((p) => {
          const active = p.id === tab;
          return (
            <button
              key={p.id}
              onClick={() => setTab(p.id)}
              className="px-3 py-2 rounded-xl font-display font-semibold text-xs whitespace-nowrap flex-shrink-0"
              style={{
                background: active ? "rgba(255,184,0,.12)" : "#12151C",
                border: `1px solid ${active ? "rgba(255,184,0,.4)" : "rgba(255,255,255,.06)"}`,
                color: active ? "#FFB800" : "rgba(245,243,238,.55)",
              }}
            >
              {p.label}
            </button>
          );
        })}
      </div>

      <div className="flex flex-col gap-3 mb-4">
        {platform.steps.map((step, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-gold/10 text-gold font-display font-bold text-[11px] flex items-center justify-center flex-shrink-0">
              {i + 1}
            </div>
            <div className="font-medium text-[13px] text-ink/75 leading-relaxed pt-0.5">{step}</div>
          </div>
        ))}
      </div>

      <button
        onClick={() => (tg?.openLink ? tg.openLink(platform.storeUrl) : window.open(platform.storeUrl, "_blank"))}
        className="w-full py-3.5 rounded-2xl bg-gold/10 border border-gold/30 font-display font-bold text-[13.5px] text-gold"
      >
        ⬇️ Скачать {platform.app} ({platform.store})
      </button>
    </BottomSheet>
  );
}
