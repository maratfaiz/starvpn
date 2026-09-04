// Shared inline SVG icons for the STAR VPN Mini App.
// Kept as simple functional components so screens/sheets stay declarative.

export function StarIcon({ size = 16, color = "#FFB800", className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} className={className}>
      <path d="M12 1l3.09 6.26L22 8.27l-5 4.87 1.18 6.88L12 16.9l-6.18 3.12L7 13.14 2 8.27l6.91-1.01L12 1z" />
    </svg>
  );
}

export function CloseIcon({ size = 12, color = "rgba(245,243,238,.6)" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.4">
      <line x1="4" y1="4" x2="20" y2="20" />
      <line x1="20" y1="4" x2="4" y2="20" />
    </svg>
  );
}

export function CheckIcon({ size = 16, color = "#FFB800", strokeWidth = "2.4" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export function ChevronIcon({ color = "rgba(245,243,238,.25)" }) {
  return (
    <svg width="7" height="12" viewBox="0 0 8 14" fill="none">
      <path d="M1 1l6 6-6 6" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TrashIcon({ size = 15, color = "rgba(245,243,238,.3)" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

export function BoltIcon({ size = 15, color = "#1A1408" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M13 2L3 14h7l-1 8 11-13h-7l1-7z" />
    </svg>
  );
}

export function GiftIcon({ size = 15, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <path d="M20 12v10H4V12" />
      <rect x="2" y="7" width="20" height="5" />
      <line x1="12" y1="22" x2="12" y2="7" />
      <path d="M12 7H7.5a2.5 2.5 0 010-5C11 2 12 7 12 7z" />
      <path d="M12 7h4.5a2.5 2.5 0 000-5C13 2 12 7 12 7z" />
    </svg>
  );
}

export function ShareIcon({ size = 14, color = "#1A1408" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.4">
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.6" y1="13.5" x2="15.4" y2="17.5" />
      <line x1="15.4" y1="6.5" x2="8.6" y2="10.5" />
    </svg>
  );
}

export function KeyIcon({ size = 16, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="15" r="4" />
      <path d="M10.8 12.2L20 3M17 6l3 3M14 9l2 2" />
    </svg>
  );
}

export function QrIcon({ size = 15, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <line x1="14" y1="14" x2="14" y2="17" />
      <line x1="14" y1="20" x2="14" y2="20.01" />
      <line x1="17" y1="14" x2="20" y2="14" />
      <line x1="20" y1="17" x2="17" y2="17" />
      <line x1="17" y1="20" x2="20" y2="20" />
    </svg>
  );
}

export function CopyIcon({ size = 15, color = "#F5F3EE" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <rect x="8" y="8" width="13" height="13" rx="2" />
      <path d="M5 16H4a1 1 0 01-1-1V4a1 1 0 011-1h11a1 1 0 011 1v1" />
    </svg>
  );
}

export function CloudIcon({ size = 16, color = "#F5F3EE" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 18a4.5 4.5 0 01-.5-8.97A5.5 5.5 0 0117 8.5a4 4 0 011 7.87" />
      <path d="M12 12v7M9.5 16.5L12 19l2.5-2.5" />
    </svg>
  );
}

export function LinkIcon({ size = 16, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 007.07 0l2.83-2.83a5 5 0 00-7.07-7.07L11.5 4.5" />
      <path d="M14 11a5 5 0 00-7.07 0L4.1 13.83a5 5 0 007.07 7.07L12.5 19.5" />
    </svg>
  );
}

export function MedalIcon({ size = 24, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M8 2L4 9l4 3 2-6-2-4zM16 2l4 7-4 3-2-6 2-4z" fill={color} opacity=".55" />
      <circle cx="12" cy="15" r="7" fill={color} />
      <circle cx="12" cy="15" r="4.2" fill="none" stroke="rgba(0,0,0,.25)" strokeWidth="1.2" />
    </svg>
  );
}

export function DiamondIcon({ size = 24, color = "#7DD3FC" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M6 3h12l4 6-10 12L2 9z" fill={color} />
      <path d="M2 9h20M6 3l2 6-4 0M18 3l-2 6 4 0M9 3l3 18 3-18" stroke="rgba(0,0,0,.2)" strokeWidth=".8" strokeLinejoin="round" />
    </svg>
  );
}

export function UsersIcon({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.5 19c0-3.2 2.9-5.5 6.5-5.5s6.5 2.3 6.5 5.5" />
      <path d="M16 4.2a3.2 3.2 0 010 6.2M21.5 19c0-2.8-2-4.9-4.8-5.4" />
    </svg>
  );
}

export function MegaphoneIcon({ size = 16, color = "currentColor", className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M3 11v2a2 2 0 002 2h1l3 5h2l-1-5h2l8 4V6l-8 4H6a2 2 0 00-2 2z" />
      <path d="M3 11V9" />
    </svg>
  );
}

export function SearchIcon({ size = 16, color = "currentColor", className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export function BanIcon({ size = 16, color = "currentColor", className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" className={className}>
      <circle cx="12" cy="12" r="9" />
      <line x1="5.5" y1="5.5" x2="18.5" y2="18.5" />
    </svg>
  );
}

export function ChartIcon({ size = 16, color = "currentColor", className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

export function RefreshIcon({ size = 16, color = "currentColor", className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
  );
}

export function RocketIcon({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2c3 2 5 6 5 10-1.5 1-3.2 1.6-5 1.6S8.5 13 7 12c0-4 2-8 5-10z" />
      <circle cx="12" cy="9" r="1.6" />
      <path d="M9 15l-2.5 2.5M15 15l2.5 2.5M9.5 19.5L12 22l2.5-2.5" />
    </svg>
  );
}

export function DownloadIcon({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v12" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="4" y1="20" x2="20" y2="20" />
    </svg>
  );
}

export function XCircleIcon({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <line x1="9" y1="9" x2="15" y2="15" />
      <line x1="15" y1="9" x2="9" y2="15" />
    </svg>
  );
}

export function AlertIcon({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="8" x2="12" y2="13" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export function LocationIcon({ size = 16, color = "#F5F3EE" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <path d="M12 22s8-7.5 8-13a8 8 0 10-16 0c0 5.5 8 13 8 13z" />
      <circle cx="12" cy="9" r="2.5" />
    </svg>
  );
}

export function DeviceIcon({ type, size, color = "#F5F3EE" }) {
  if (type === "laptop") {
    return (
      <svg width={size ?? 18} height={size ?? 18} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <rect x="3" y="4" width="18" height="12" rx="1.5" />
        <line x1="2" y1="20" x2="22" y2="20" />
      </svg>
    );
  }
  if (type === "tablet") {
    return (
      <svg width={size ?? 17} height={size ?? 17} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <rect x="4" y="2" width="16" height="20" rx="2" />
        <line x1="12" y1="18" x2="12.01" y2="18" />
      </svg>
    );
  }
  return (
    <svg width={size ?? 16} height={size ?? 16} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <rect x="7" y="2" width="10" height="20" rx="2" />
      <line x1="11" y1="18" x2="13" y2="18" />
    </svg>
  );
}

export function SettingIcon({ name, size = 14, color = "#F5F3EE" }) {
  switch (name) {
    case "bell":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 01-3.46 0" />
        </svg>
      );
    case "globe":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 010 20 15.3 15.3 0 010-20z" />
        </svg>
      );
    case "shield":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z" />
        </svg>
      );
    case "info":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      );
    case "help":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.1 9a3 3 0 015.83 1c0 2-3 2-3 4" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      );
    default:
      return null;
  }
}

export function CrownIcon({ size = 21, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round">
      <path d="M3 17h18l-1.5-9-4.5 3.5L12 6 8.5 11.5 4 8z" />
      <line x1="4" y1="20" x2="20" y2="20" />
    </svg>
  );
}

export function CalendarIcon({ size = 16, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="16" y1="2" x2="16" y2="6" />
    </svg>
  );
}

export function CardIcon({ size = 16, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <line x1="2" y1="10" x2="22" y2="10" />
    </svg>
  );
}

export function HeadsetIcon({ size = 16, color = "#FFB800" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 13v-1a8 8 0 0116 0v1" />
      <rect x="2.5" y="13" width="4" height="6" rx="1.5" />
      <rect x="17.5" y="13" width="4" height="6" rx="1.5" />
      <path d="M19.5 19v.5a3 3 0 01-3 3H13" />
    </svg>
  );
}

export function NavIcon({ name, color, size = 21 }) {
  switch (name) {
    case "home":
      return <CrownIcon size={size} color={color} />;
    case "devices":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <rect x="3" y="4" width="18" height="12" rx="1.5" />
          <line x1="2" y1="20" x2="22" y2="20" />
        </svg>
      );
    case "referral":
      return <ShareIcon size={size} color={color} />;
    case "account":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      );
    case "admin":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14M12 2v2M12 20v2M2 12h2M20 12h2" />
        </svg>
      );
    default:
      return null;
  }
}

export function GearIcon({ size = 16, color = "rgba(245,243,238,.35)" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.5a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.73l.15-.1a2 2 0 00.73-2.72l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
