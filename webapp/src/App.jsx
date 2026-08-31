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

import * as api from "./data/mockApi.js";
import {
  referral,
  daysHistoryInitial,
  account,
  settingsRows,
  notificationTogglesInitial,
  languageOptions,
  renewPlans,
  giftDayOptions,
} from "./data/mockData.js";

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

function meToSubscription(me) {
  return {
    active: me.subscription_active,
    trialUsed: me.trial_used,
    planName: me.plan_name,
    daysLeft: me.days_left,
    totalDays: me.total_days,
    expiryDate: new Date(me.expires_at).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" }),
    connectionLabel: "Подключено",
  };
}

export default function App() {
  const [telegramOk] = useState(hasTelegramSession);
  const [showOnboarding, setShowOnboarding] = useState(() => telegramOk && !onboardingSeen());
  const [tgUser, setTgUser] = useState(null);

  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState(null);
  const [devices, setDevices] = useState([]);
  const [maxDevices, setMaxDevices] = useState(3);
  const [isAdmin, setIsAdmin] = useState(false);
  const [pendingGift, setPendingGift] = useState(null);

  const loadAll = async () => {
    const [me, devs, admin] = await Promise.all([api.getMe(), api.getDevices(), api.adminCheck()]);
    setSubscription(meToSubscription(me));
    setMaxDevices(me.max_devices);
    setDevices(devs);
    setIsAdmin(admin.is_admin);
  };

  useEffect(() => {
    if (!telegramOk) return;
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      setTgUser(tg.initDataUnsafe?.user || null);
    }

    loadAll().then(() => {
      setLoading(false);
      api.checkGiftNotification().then(setPendingGift);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telegramOk]);

  // navigation
  const [activeTab, setActiveTab] = useState("home");

  // mutable app state (mock, no backend yet)
  const [daysHistory, setDaysHistory] = useState(daysHistoryInitial);
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
  const [giftDays, setGiftDays] = useState(7);
  const [giftComment, setGiftComment] = useState("");

  // renew sheet
  const [renewOpen, setRenewOpen] = useState(false);
  const [renewStep, setRenewStep] = useState("form");
  const [renewMethod, setRenewMethod] = useState("stars");
  const [customDays, setCustomDays] = useState(90);
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
    setGiftDays(7);
    setGiftComment("");
    setGiftStep("form");
  };
  const submitGift = () => {
    if (!giftUsername.trim()) return;
    haptic("notification");
    setGiftStep("success");
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
  const submitRenew = () => {
    const basePlan = renewPlans[0];
    const pricePerDay = basePlan.price / basePlan.days;
    const rubPerDay = basePlan.rub / basePlan.days;
    const plan = {
      label: `${customDays} дней`,
      days: customDays,
      price: Math.max(1, Math.round(customDays * pricePerDay)),
      rub: Math.max(1, Math.round(customDays * rubPerDay)),
    };

    haptic("notification");

    if (renewMethod === "card") {
      // Real endpoint: POST /api/invoice/card -> tg.openLink(Robokassa url);
      // confirmation arrives later via the /card/webhook ResultURL, so we
      // don't touch the subscription state here — only the invoice was created.
      // NOTE: per ADR-015, /api/invoice/card only supports the 3 fixed plan
      // tiers, not arbitrary day counts — now that this sheet always offers
      // a custom-days slider, wiring the "Карта" tab to the real endpoint
      // needs either extending that endpoint or hiding "Карта" here and
      // keeping it fixed-tier elsewhere. Flagged, not resolved by this mock.
      setRenewOpen(false);
      showToast("💳 Счёт создан — оплати картой на защищённой странице");
      return;
    }

    // Stars: tg.openInvoice resolves synchronously with a paid/failed status
    // in the real app, so we can apply the days right away.
    setSubscription((s) => ({
      ...s,
      active: true,
      daysLeft: s.daysLeft + plan.days,
      totalDays: s.totalDays + plan.days,
    }));
    setDaysHistory((h) => [
      { id: Date.now(), label: `Продление: ${plan.label}`, date: "только что", days: plan.days, type: "purchase" },
      ...h,
    ]);
    setLastAddedDays(plan.days);
    setRenewStep("success");
    setJustRenewed(true);
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

  const copyPrimaryDeviceLink = async (device) => {
    haptic("light");
    const { link } = await api.getDeviceLink(device.id);
    navigator.clipboard?.writeText(link).catch(() => {});
    showToast("✅ Ссылка скопирована!");
  };

  const copyDeviceSubUrl = () => {
    navigator.clipboard?.writeText(subSheet.subUrl).catch(() => {});
    showToast("✅ Ссылка подписки скопирована!");
  };

  const copyReferralCode = () => {
    haptic("light");
    navigator.clipboard?.writeText(referral.code).catch(() => {});
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 1800);
  };

  const shareReferralLink = () => {
    haptic("light");
    const link = `https://t.me/starisvpnbot?start=${referral.code}`;
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
    if (pendingGift) {
      await api.acceptGift(pendingGift.id);
      setSubscription((s) => ({ ...s, daysLeft: s.daysLeft + pendingGift.days, totalDays: s.totalDays + pendingGift.days }));
    }
    setPendingGift(null);
  };

  const selectedDevice = devices.find((d) => d.id === deviceSheetId) || null;
  const totalTrafficGb = devices.reduce((sum, d) => sum + (d.traffic_gb || 0), 0);

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
              primaryDevice={devices[0] || null}
              devicesCount={devices.length}
              devicesLimit={maxDevices}
              trafficUsedTotal={totalTrafficGb.toFixed(1)}
              onShowKey={showDeviceLink}
              onCopyKey={copyPrimaryDeviceLink}
              onAddDevice={openAddDevice}
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
              daysHistory={daysHistory}
              copied={codeCopied}
              onCopyCode={copyReferralCode}
              onShare={shareReferralLink}
            />
          )}
          {activeTab === "account" && (
            <AccountScreen
              account={{ ...account, name: tgUser ? `${tgUser.first_name}${tgUser.last_name ? " " + tgUser.last_name : ""}` : account.name }}
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
      />

      <RenewSheet
        open={renewOpen}
        step={renewStep}
        onClose={closeRenew}
        plans={renewPlans}
        method={renewMethod}
        onSelectMethod={setRenewMethod}
        customDays={customDays}
        onCustomDaysChange={setCustomDays}
        onSubmit={submitRenew}
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
