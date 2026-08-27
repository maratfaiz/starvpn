import { NavIcon } from "./icons.jsx";

const TABS = [
  { id: "home", label: "Главная", icon: "home" },
  { id: "devices", label: "Устройства", icon: "devices" },
  { id: "referral", label: "Рефералы", icon: "referral" },
  { id: "account", label: "Аккаунт", icon: "account" },
];

const ADMIN_TAB = { id: "admin", label: "Админ", icon: "admin" };

export default function BottomNav({ active, onChange, showAdmin }) {
  const tabs = showAdmin ? [...TABS, ADMIN_TAB] : TABS;
  return (
    <div
      className="flex flex-shrink-0 px-3 pt-2 bg-app-bg border-t border-white/[.06]"
      style={{ paddingBottom: "calc(8px + env(safe-area-inset-bottom, 0px))" }}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        const color = isActive ? "#FFB800" : "rgba(235,224,204,.4)";
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className="flex-1 flex flex-col items-center gap-1 py-1.5"
          >
            <NavIcon name={tab.icon} color={color} />
            <span className="font-display font-semibold text-[10.5px]" style={{ color }}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
