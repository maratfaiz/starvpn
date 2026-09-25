import { useEffect, useRef, useState } from "react";

import BottomNav from "./components/BottomNav.jsx";
import Toast from "./components/Toast.jsx";
import Starfield from "./components/Starfield.jsx";
import Onboarding, { onboardingSeen } from "./components/Onboarding.jsx";
import TelegramGate from "./components/TelegramGate.jsx";
import GiftReceivedModal from "./components/GiftReceivedModal.jsx";

import HomeScreen from "./screens/HomeScreen.jsx";
import DevicesScreen from "./screens/DevicesScreen.jsx";
import ReferralsScreen from "./screens/ReferralsScreen.jsx";
import AccountScreen from "./screens/AccountScreen.jsx";
import AdminScreen from "./screens/AdminScreen.jsx";

import SettingsSheet from "./sheets/SettingsSheet.jsx";
import GiftSheet from "./sheets/GiftSheet.jsx";
import RenewSheet from "./sheets/RenewSheet.jsx";
import DeviceSheet from "./sheets/DeviceSheet.jsx";
import AddDeviceSheet from "./sheets/AddDeviceSheet.jsx";
import DeviceLinkSheet from "./sheets/DeviceLinkSheet.jsx";
import SubscriptionLinkSheet from "./sheets/SubscriptionLinkSheet.jsx";
import InstructionsSheet from "./sheets/InstructionsSheet.jsx";

import * as api from "./data/api.js";
import {
  account,
  settingsRows,
  notificationTogglesInitial,
  languageOptions,
  giftDayOptions,
} from "./data/staticData.js";

// Gift days are limited to the Stars plans bot/api.py actually has
// (_PLANS_API: plan_1m/plan_3m/plan_6m = 30/90/180 days).
const GIFT_PLAN_BY_DAYS = { 30: "plan_1m", 90: "plan_3m", 180: "plan_6m" };

// Vite sets import.meta.env.DEV=true only for `npm run dev` / local preview —
// lets us exercise the app outside Telegram while still gating production
// builds behind a real Telegram WebApp session, like the real bot does.
function hasTelegramSession() {
  const tg = window.Telegram?.WebApp;
  return !!tg?.initData || import.meta.env.DEV;
}

function haptic(type = "impact") {
  const tg = window.Telegram?.WebApp;
  if (type === "notification") {
    tg?.HapticFeedback?.notificationOccurred?.("success");
  } else {
    tg?.HapticFeedback?.impactOccurred?.(type);
  }
}

// bot/api.py sends naive datetimes (datetime.utcnow().isoformat(), no "Z" /
// offset) that are always UTC. `new Date(...)` treats a date-time string
// with no offset as browser-LOCAL time, which would silently skew every
// computation below by the viewer's UTC offset — so parse it as UTC ourselves.
function parseUtc(isoString) {
  if (!isoString) return null;
  const hasOffset = /Z$|[+-]\d\d:\d\d$/.test(isoString);
  return new Date(hasOffset ? isoString : `${isoString}Z`);
}

function meToSubscription(me) {
  const exp = parseUtc(me.subscription_expires_at);
  const daysLeft = exp ? Math.max(0, Math.floor((exp.getTime() - Date.now()) / 86400000)) : 0;
  return {
    active: me.subscription_active,
    trialUsed: me.trial_used,
    daysLeft,
    expiryDate: exp ? exp.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" }) : "",
    connectionLabel: "Подключено",
  };
}

function meToServer(me) {
  return {
    flag: me.server_flag,
    name: me.server_city,
    protocol: me.server_protocol,
  };
}

export default function App() {
  const [telegramOk] = useState(hasTelegramSession);
  const [showOnboarding, setShowOnboarding] = useState(() => telegramOk && !onboardingSeen());
  const [tgUser, setTgUser] = useState(null);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [subscription, setSubscription] = useState(null);
  const [server, setServer] = useState(null);
  const [devices, setDevices] = useState([]);
  const [maxDevices, setMaxDevices] = useState(3);
  const [isAdmin, setIsAdmin] = useState(false);
  const [pendingGift, setPendingGift] = useState(null);
  const [referral, setReferral] = useState(null);
  const [renewPlans, setRenewPlans] = useState([]);
  const [profile, setProfile] = useState({ full_name: "", username: "" });

  const loadAll = async () => {
    const [me, devs, admin, ref, plans] = await Promise.all([
      api.getMe(),
      api.getDevices(),
      api.adminCheck(),
      api.getReferral(),
      api.getRenewPlans(),
    ]);
    setSubscription(meToSubscription(me));
    setServer(meToServer(me));
    setMaxDevices(me.max_devices);
    setDevices(devs);
    setIsAdmin(admin.is_admin);
    setReferral(ref);
    setRenewPlans(plans);
    setProfile({ full_name: me.full_name, username: me.username });
  };

  useEffect(() => {
    if (!telegramOk) return;
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      setTgUser(tg.initDataUnsafe?.user || null);
    }

    setLoadError(false);
    loadAll()
      .then(() => {
        setLoading(false);
        api.checkGiftNotification().then(setPendingGift).catch(() => {});
      })
      .catch(() => {
        // Network/auth failure on first load — stop spinning and let the
        // person retry instead of staring at "Загрузка" forever.
        setLoading(false);
        setLoadError(true);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telegramOk]);

  const retryLoad = () => {
    setLoading(true);
    setLoadError(false);
    loadAll()
      .then(() => setLoading(false))
      .catch(() => {
        setLoading(false);
        setLoadError(true);
      });
  };

  // navigation
  const [activeTab, setActiveTab] = useState("home");

  // auto-server toggle is a client-only preference for now — there's only
  // one real server (Amsterdam), nothing backend-side reads this yet.
  const [autoServer, setAutoServer] = useState(true);
  const [trialActivating, setTrialActivating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // toast
  const [toast, setToast] = useState("");
  const toastTimer = useRef(null);
  const showToast = (message) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 2200);
  };

  // settings sheet
  const [settingId, setSettingId] = useState(null);
  const [notificationToggles, setNotificationToggles] = useState(notificationTogglesInitial);
  const [selectedLanguage, setSelectedLanguage] = useState("ru");

  // gift sheet (send)
  const [giftOpen, setGiftOpen] = useState(false);
  const [giftStep, setGiftStep] = useState("form");
  const [giftUsername, setGiftUsername] = useState("");
  const [giftDays, setGiftDays] = useState(30);
  const [giftComment, setGiftComment] = useState("");
  const [giftSubmitting, setGiftSubmitting] = useState(false);

  // renew sheet
  const [renewOpen, setRenewOpen] = useState(false);
  const [renewStep, setRenewStep] = useState("form");
  const [renewPlanId, setRenewPlanId] = useState("plan_3m");
  const [renewMethod, setRenewMethod] = useState("stars");
  const [renewSubmitting, setRenewSubmitting] = useState(false);
  const [customDays, setCustomDays] = useState(14);
  const [lastAddedDays, setLastAddedDays] = useState(0);
  const [justRenewed, setJustRenewed] = useState(false);

  // device sheets
  const [deviceSheetId, setDeviceSheetId] = useState(null);
  const [addDeviceOpen, setAddDeviceOpen] = useState(false);
  const [addingDevice, setAddingDevice] = useState(false);
  const [linkSheet, setLinkSheet] = useState(null); // { name, link }
  const [subSheet, setSubSheet] = useState(null); // { name, subUrl }

  // instructions
  const [instructionsOpen, setInstructionsOpen] = useState(false);

  // referral copy state
  const [codeCopied, setCodeCopied] = useState(false);

  const changeTab = (tab) => {
    haptic("light");
    setActiveTab(tab);
  };

  const openSetting = (id) => {
    haptic("light");
    setSettingId(id);
  };
  const closeSettings = () => setSettingId(null);
  const toggleNotification = (id) => {
    haptic("light");
    setNotificationToggles((prev) => prev.map((t) => (t.id === id ? { ...t, on: !t.on } : t)));
  };
  const selectLanguage = (id) => {
    haptic("light");
    setSelectedLanguage(id);
  };

  const openGift = () => {
    haptic("light");
    setGiftOpen(true);
    setGiftStep("form");
  };
  const closeGift = () => {
    setGiftOpen(false);
    setGiftUsername("");
    setGiftDays(30);
    setGiftComment("");
    setGiftStep("form");
  };
  const submitGift = async () => {
    if (!giftUsername.trim()) return;
    const planKey = GIFT_PLAN_BY_DAYS[giftDays];
    setGiftSubmitting(true);
    try {
      const { url } = await api.createGiftInvoice({
        planKey,
        recipient: giftUsername.trim(),
        message: giftComment.trim(),
      });
      const status = await api.openTelegramInvoice(url);
      if (status === "paid") {
        haptic("notification");
        setGiftStep("success");
      } else if (status !== "pending") {
        showToast("Оплата отменена");
      }
    } catch (e) {
      showToast("❌ " + e.message);
    } finally {
      setGiftSubmitting(false);
    }
  };

  const openRenew = () => {
    haptic("light");
    setRenewOpen(true);
    setRenewStep("form");
  };
  const closeRenew = () => {
    setRenewOpen(false);
    setRenewStep("form");
    if (justRenewed) {
      setJustRenewed(false);
      setInstructionsOpen(true);
    }
  };
  const submitRenew = async () => {
    const isCustom = renewPlanId === "custom";
    if (isCustom && renewMethod === "stars") {
      showToast("Свой срок доступен только при оплате картой");
      return;
    }

    const plan = isCustom ? null : renewPlans.find((p) => p.id === renewPlanId);
    setRenewSubmitting(true);
    try {
      const { url } = await api.createRenewInvoice({
        planKey: isCustom ? null : renewPlanId,
        method: renewMethod,
        days: isCustom ? customDays : undefined,
      });

      if (renewMethod === "card") {
        // Hosted Robokassa page — confirmation arrives later via the
        // /card/webhook ResultURL, so we can't apply days right away.
        api.openExternalPayment(url);
        setRenewOpen(false);
        showToast("💳 Счёт создан — оплати картой на защищённой странице");
        return;
      }

      haptic("notification");
      const status = await api.openTelegramInvoice(url);
      if (status === "paid") {
        await loadAll();
        setLastAddedDays(plan.days);
        setRenewStep("success");
        setJustRenewed(true);
      } else if (status !== "pending") {
        showToast("Оплата отменена");
      }
    } catch (e) {
      showToast("❌ " + e.message);
    } finally {
      setRenewSubmitting(false);
    }
  };

  const activateTrial = async () => {
    setTrialActivating(true);
    try {
      const me = await api.activateTrial();
      setSubscription(meToSubscription(me));
      haptic("notification");
      showToast("🎁 Триал активирован на 2 дня!");
    } finally {
      setTrialActivating(false);
    }
  };

  const openDevice = (id) => {
    haptic("light");
    setDeviceSheetId(id);
  };
  const closeDevice = () => setDeviceSheetId(null);

  const deleteDevice = async (id) => {
    haptic("notification");
    await api.deleteDevice(id);
    setDevices((prev) => prev.filter((d) => d.id !== id));
    setDeviceSheetId(null);
    showToast("✅ Устройство удалено");
  };

  const openAddDevice = () => {
    haptic("light");
    setAddDeviceOpen(true);
  };
  const submitAddDevice = async (type, label) => {
    setAddingDevice(true);
    try {
      const device = await api.addDevice(type, label);
      setDevices((prev) => [...prev, device]);
      setAddDeviceOpen(false);
      setDeviceSheetId(device.id);
      showToast("✅ Устройство добавлено");
    } finally {
      setAddingDevice(false);
    }
  };

  const showDeviceLink = async (device) => {
    haptic("light");
    const { link } = await api.getDeviceLink(device.id);
    setDeviceSheetId(null);
    setLinkSheet({ name: device.name, link });
  };

  const showDeviceSublink = async (device) => {
    haptic("light");
    const { sub_url } = await api.getDeviceLink(device.id);
    setDeviceSheetId(null);
    setSubSheet({ name: device.name, subUrl: sub_url });
  };

  const copyDeviceLink = () => {
    navigator.clipboard?.writeText(linkSheet.link).catch(() => {});
    showToast("✅ Ссылка скопирована!");
  };

  const copyDeviceSubUrl = () => {
    navigator.clipboard?.writeText(subSheet.subUrl).catch(() => {});
    showToast("✅ Ссылка подписки скопирована!");
  };

  const copyReferralCode = () => {
    if (!referral) return;
    haptic("light");
    navigator.clipboard?.writeText(referral.link).catch(() => {});
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 1800);
  };

  const shareReferralLink = () => {
    if (!referral) return;
    haptic("light");
    const link = referral.link;
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}`);
    } else if (navigator.share) {
      navigator.share({ url: link }).catch(() => {});
    } else {
      navigator.clipboard?.writeText(link).catch(() => {});
      showToast("Ссылка скопирована");
    }
  };

  const toggleAutoServer = () => {
    haptic("light");
    setAutoServer((v) => !v);
  };

  const logout = () => {
    haptic("light");
    showToast("Функция выхода скоро появится");
  };

  const refreshAll = async () => {
    setRefreshing(true);
    showToast("Обновляю...");
    try {
      await loadAll();
      showToast("✅ Обновлено");
    } finally {
      setRefreshing(false);
    }
  };

  const closeGiftReceived = async () => {
    // The days were already granted server-side when the gift's payment
    // webhook fired — this just marks the notification as read.
    if (pendingGift) {
      await api.acceptGift(pendingGift.id);
    }
    setPendingGift(null);
  };

  const selectedDevice = devices.find((d) => d.id === deviceSheetId) || null;
  const totalTrafficGb = devices.reduce((sum, d) => sum + (d.traffic_gb || 0), 0);

  const displayName = tgUser
    ? `${tgUser.first_name}${tgUser.last_name ? " " + tgUser.last_name : ""}`
    : profile.full_name || "STAR VPN";
  const displayUsername = tgUser?.username ? `@${tgUser.username}` : profile.username ? `@${profile.username}` : "";
  const initials = displayName.trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "SV";

  if (!telegramOk) {
    return <TelegramGate />;
  }

  if (showOnboarding) {
    return (
      <Onboarding
        trialUsed={subscription?.trialUsed ?? false}
        onFinish={(action) => {
          setShowOnboarding(false);
          if (action === "buy") setRenewOpen(true);
          if (action === "trial") activateTrial();
        }}
      />
    );
  }

  if (loadError) {
    return (
      <div className="relative flex items-center justify-center min-h-screen bg-app-bg overflow-hidden">
        <Starfield shootingStars />
        <div className="relative z-[1] flex flex-col items-center gap-4 px-8 text-center">
          <span className="font-display font-extrabold text-xl text-ink">Не удалось загрузить данные</span>
          <span className="text-ink/45 text-sm">Проверь соединение и попробуй ещё раз</span>
          <button
            onClick={retryLoad}
            className="mt-2 border-none px-5 py-3 rounded-2xl bg-gradient-to-br from-gold to-gold-dark font-display font-bold text-sm text-[#1A1408]"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  if (loading || !subscription) {
    return (
      <div className="relative flex items-center justify-center min-h-screen bg-app-bg overflow-hidden">
        <Starfield shootingStars />
        <div className="relative z-[1] flex flex-col items-center gap-6">
          <div className="flex flex-col items-center gap-2">
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7 text-gold">
              <path d="M12 2l1.5 6.5L20 10l-6.5 1.5L12 18l-1.5-6.5L4 10l6.5-1.5z" />
            </svg>
            <span className="font-display font-extrabold text-2xl tracking-wide text-gold">STAR VPN</span>
          </div>
          <span className="text-ink/40 text-xs tracking-[0.2em] uppercase animate-pulse">Загрузка</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-screen bg-app-bg overflow-hidden">
      <Starfield />
      <div className="relative z-[1] flex flex-col h-full">
        <div className="flex-1 overflow-y-auto px-5 pt-5 pb-6">
          {activeTab === "home" && (
            <HomeScreen
              subscription={subscription}
              server={server}
              trafficUsedTotal={totalTrafficGb.toFixed(1)}
              autoServer={autoServer}
              onToggleAutoServer={toggleAutoServer}
              onOpenRenew={openRenew}
              onOpenGift={openGift}
              onActivateTrial={activateTrial}
              trialActivating={trialActivating}
            />
          )}
          {activeTab === "devices" && (
            <DevicesScreen
              devices={devices}
              devicesLimit={maxDevices}
              totalTrafficGb={totalTrafficGb}
              onOpenDevice={openDevice}
              onAddDevice={openAddDevice}
            />
          )}
          {activeTab === "referral" && (
            <ReferralsScreen
              referral={referral}
              copied={codeCopied}
              onCopyCode={copyReferralCode}
              onShare={shareReferralLink}
            />
          )}
          {activeTab === "account" && (
            <AccountScreen
              account={{ ...account, name: displayName, username: displayUsername, initials }}
              subscription={subscription}
              settingsRows={settingsRows}
              onOpenSetting={openSetting}
              onManageSubscription={openRenew}
              onLogout={logout}
              onOpenInstructions={() => setInstructionsOpen(true)}
              onRefresh={refreshAll}
              refreshing={refreshing}
            />
          )}
          {activeTab === "admin" && isAdmin && <AdminScreen showToast={showToast} />}
        </div>

        <BottomNav active={activeTab} onChange={changeTab} showAdmin={isAdmin} />
      </div>

      <SettingsSheet
        settingId={settingId}
        onClose={closeSettings}
        notificationToggles={notificationToggles}
        onToggleNotification={toggleNotification}
        languageOptions={languageOptions}
        selectedLanguage={selectedLanguage}
        onSelectLanguage={selectLanguage}
        appVersion={account.appVersion}
      />

      <GiftSheet
        open={giftOpen}
        step={giftStep}
        onClose={closeGift}
        dayOptions={giftDayOptions}
        username={giftUsername}
        days={giftDays}
        comment={giftComment}
        onUsernameChange={setGiftUsername}
        onDaysSelect={setGiftDays}
        onCommentChange={setGiftComment}
        onSubmit={submitGift}
        submitting={giftSubmitting}
      />

      <RenewSheet
        open={renewOpen}
        step={renewStep}
        onClose={closeRenew}
        plans={renewPlans}
        selectedPlanId={renewPlanId}
        onSelectPlan={setRenewPlanId}
        method={renewMethod}
        onSelectMethod={setRenewMethod}
        customDays={customDays}
        onCustomDaysChange={setCustomDays}
        onSubmit={submitRenew}
        submitting={renewSubmitting}
        lastAddedDays={lastAddedDays}
      />

      <DeviceSheet
        open={!!deviceSheetId}
        device={selectedDevice}
        onClose={closeDevice}
        onDelete={deleteDevice}
        onShowLink={showDeviceLink}
        onShowSubscription={showDeviceSublink}
      />

      <AddDeviceSheet open={addDeviceOpen} onClose={() => setAddDeviceOpen(false)} onSubmit={submitAddDevice} submitting={addingDevice} />

      <DeviceLinkSheet
        open={!!linkSheet}
        deviceName={linkSheet?.name}
        link={linkSheet?.link}
        onClose={() => setLinkSheet(null)}
        onCopy={copyDeviceLink}
      />

      <SubscriptionLinkSheet
        open={!!subSheet}
        deviceName={subSheet?.name}
        subUrl={subSheet?.subUrl}
        onClose={() => setSubSheet(null)}
        onCopy={copyDeviceSubUrl}
      />

      <InstructionsSheet open={instructionsOpen} onClose={() => setInstructionsOpen(false)} />

      <GiftReceivedModal gift={pendingGift} onClose={closeGiftReceived} />

      <Toast message={toast} />
    </div>
  );
}
