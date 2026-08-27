import BottomSheet from "../components/BottomSheet.jsx";
import { CheckIcon } from "../components/icons.jsx";

const TITLES = {
  notifications: "Уведомления",
  language: "Язык",
  privacy: "Конфиденциальность",
  support: "Поддержка",
  about: "О приложении",
};

export default function SettingsSheet({
  settingId,
  onClose,
  notificationToggles,
  onToggleNotification,
  languageOptions,
  selectedLanguage,
  onSelectLanguage,
  appVersion,
}) {
  return (
    <BottomSheet open={!!settingId} onClose={onClose} title={settingId ? TITLES[settingId] : ""} maxHeight="70%">
      {settingId === "notifications" && (
        <div className="flex flex-col gap-3">
          {notificationToggles.map((t) => (
            <button
              key={t.id}
              onClick={() => onToggleNotification(t.id)}
              className="flex items-center justify-between px-3.5 py-3 bg-app-card border border-white/[.06] rounded-[14px]"
            >
              <span className="font-medium text-[13.5px] text-ink">{t.label}</span>
              <div
                className="w-10 h-[23px] rounded-full relative"
                style={{ background: t.on ? "linear-gradient(135deg,#FFB800,#D99B00)" : "rgba(255,255,255,.1)" }}
              >
                <div
                  className="absolute top-0.5 w-[19px] h-[19px] rounded-full bg-[#1A1408] transition-all"
                  style={{ left: t.on ? "19px" : "2px" }}
                />
              </div>
            </button>
          ))}
        </div>
      )}

      {settingId === "language" && (
        <div className="flex flex-col gap-2">
          {languageOptions.map((lang) => (
            <button
              key={lang.id}
              onClick={() => onSelectLanguage(lang.id)}
              className="flex items-center justify-between px-3.5 py-3.5 bg-app-card border border-white/[.06] rounded-[14px]"
            >
              <span className="font-medium text-[13.5px] text-ink">{lang.label}</span>
              {selectedLanguage === lang.id && <CheckIcon />}
            </button>
          ))}
        </div>
      )}

      {settingId === "privacy" && (
        <p className="font-medium text-[13.5px] text-ink/60 leading-relaxed">
          Мы не ведём журнал посещённых сайтов и не передаём данные третьим лицам. Шифрование AES-256, политика
          no-logs.
        </p>
      )}

      {settingId === "about" && (
        <div className="flex flex-col gap-2.5">
          <div className="flex justify-between">
            <span className="font-medium text-[13px] text-ink/45">Версия</span>
            <span className="font-semibold text-[13px] text-ink">{appVersion}</span>
          </div>
          <div className="flex justify-between">
            <span className="font-medium text-[13px] text-ink/45">Платформа</span>
            <span className="font-semibold text-[13px] text-ink">Telegram Mini App</span>
          </div>
        </div>
      )}

      {settingId === "support" && (
        <div className="flex flex-col gap-2">
          <div className="px-3.5 py-3.5 bg-app-card border border-white/[.06] rounded-[14px] font-medium text-[13.5px] text-ink">
            Написать в поддержку
          </div>
          <div className="px-3.5 py-3.5 bg-app-card border border-white/[.06] rounded-[14px] font-medium text-[13.5px] text-ink">
            Частые вопросы
          </div>
        </div>
      )}
    </BottomSheet>
  );
}
