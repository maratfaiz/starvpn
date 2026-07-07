import { useEffect, useRef, useState } from "react";

import Header from "./components/Header.jsx";
import BottomNav from "./components/BottomNav.jsx";
import Toast from "./components/Toast.jsx";

import HomeScreen from "./screens/HomeScreen.jsx";
import DevicesScreen from "./screens/DevicesScreen.jsx";
import ReferralsScreen from "./screens/ReferralsScreen.jsx";
import AccountScreen from "./screens/AccountScreen.jsx";

import SettingsSheet from "./sheets/SettingsSheet.jsx";
import GiftSheet from "./sheets/GiftSheet.jsx";
import RenewSheet from "./sheets/RenewSheet.jsx";
import DeviceSheet from "./sheets/DeviceSheet.jsx";
import TopupSheet from "./sheets/TopupSheet.jsx";

import {
  subscription as subscriptionMock,
  server,
  speedValue,
  trafficUsedTotal,
  trafficBars,
  starsBalanceInitial,
  devicesInitial,
  devicesLimit,
  referral,
  rewardTiers,
  daysHistoryInitial,
  account,
  settingsRows,
  notificationTogglesInitial,
  languageOptions,
  renewPlans,
  giftDayOptions,
  topupPacks,
} from "./data/mockData.js";

function haptic(type = "impact") {
  const tg = window.Telegram?.WebApp;
  if (type === "notification") {
    tg?.HapticFeedback?.notificationOccurred?.("success");
  } else {
    tg?.HapticFeedback?.impactOccurred?.(type);
  }
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [tgUser, setTgUser] = useState(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      setTgUser(tg.initDataUnsafe?.user || null);
    }
    setReady(true);
  }, []);

  // navigation
  const [activeTab, setActiveTab] = useState("home");

  // mutable app state (mock, no backend yet)
  const [subscription, setSubscription] = useState(subscriptionMock);
  const [starsBalance, setStarsBalance] = useState(starsBalanceInitial);
  const [devices, setDevices] = useState(devicesInitial);
  const [daysHistory, setDaysHistory] = useState(daysHistoryInitial);
  const [autoServer, setAutoServer] = useState(true);

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

  // gift sheet
  const [giftOpen, setGiftOpen] = useState(false);
  const [giftStep, setGiftStep] = useState("form");
  const [giftUsername, setGiftUsername] = useState("");
  const [giftDays, setGiftDays] = useState(7);
  const [giftComment, setGiftComment] = useState("");

  // renew sheet
  const [renewOpen, setRenewOpen] = useState(false);
  const [renewStep, setRenewStep] = useState("form");
  const [renewPlanId, setRenewPlanId] = useState(2);
  const [lastAddedDays, setLastAddedDays] = useState(0);

  // device sheet
  const [deviceSheetId, setDeviceSheetId] = useState(null);

  // topup sheet
  const [topupOpen, setTopupOpen] = useState(false);
  const [topupStep, setTopupStep] = useState("form");
  const [topupPackId, setTopupPackId] = useState(2);

  // referral copy state
  const [codeCopied, setCodeCopied] = useState(false);

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <span className="text-ink/50 text-sm animate-pulse">Загрузка...</span>
      </div>
    );
  }

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
  };
  const submitRenew = () => {
    const plan = renewPlans.find((p) => p.id === renewPlanId) || renewPlans[0];
    haptic("notification");
    setSubscription((s) => ({ ...s, daysLeft: s.daysLeft + plan.days, totalDays: s.totalDays + plan.days }));
    setDaysHistory((h) => [
      { id: Date.now(), label: `Продление: ${plan.label}`, date: "только что", days: plan.days, type: "purchase" },
      ...h,
    ]);
    setLastAddedDays(plan.days);
    setRenewStep("success");
  };

  const openDevice = (id) => {
    haptic("light");
    setDeviceSheetId(id);
  };
  const closeDevice = () => setDeviceSheetId(null);
  const deleteDevice = (id) => {
    haptic("notification");
    setDevices((prev) => prev.filter((d) => d.id !== id));
    setDeviceSheetId(null);
    showToast("Устройство удалено");
  };

  const openTopup = () => {
    haptic("light");
    setTopupOpen(true);
    setTopupStep("form");
  };
  const closeTopup = () => {
    setTopupOpen(false);
    setTopupStep("form");
  };
  const submitTopup = () => {
    const pack = topupPacks.find((p) => p.id === topupPackId) || topupPacks[0];
    haptic("notification");
    setStarsBalance((b) => b + pack.stars);
    setTopupStep("success");
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

  const toggleAutoServer = () => {
    haptic("light");
    setAutoServer((v) => !v);
  };

  const logout = () => {
    haptic("light");
    showToast("Функция выхода скоро появится");
  };

  const selectedDevice = devices.find((d) => d.id === deviceSheetId) || null;

  return (
    <div className="flex flex-col h-screen bg-app-bg">
      <Header starsBalance={starsBalance} onOpenTopup={openTopup} />

      <div className="flex-1 overflow-y-auto px-5 pb-6">
        {activeTab === "home" && (
          <HomeScreen
            subscription={subscription}
            server={server}
            speedValue={speedValue}
            trafficUsedTotal={trafficUsedTotal}
            autoServer={autoServer}
            onToggleAutoServer={toggleAutoServer}
            onOpenRenew={openRenew}
            onOpenGift={openGift}
          />
        )}
        {activeTab === "devices" && (
          <DevicesScreen
            devices={devices}
            devicesLimit={devicesLimit}
            trafficUsedTotal={trafficUsedTotal}
            trafficBars={trafficBars}
            onOpenDevice={openDevice}
          />
        )}
        {activeTab === "referral" && (
          <ReferralsScreen
            referral={referral}
            rewardTiers={rewardTiers}
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
          />
        )}
      </div>

      <BottomNav active={activeTab} onChange={changeTab} />

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
        selectedPlanId={renewPlanId}
        onSelectPlan={setRenewPlanId}
        onSubmit={submitRenew}
        lastAddedDays={lastAddedDays}
      />

      <DeviceSheet open={!!deviceSheetId} device={selectedDevice} onClose={closeDevice} onDelete={deleteDevice} />

      <TopupSheet
        open={topupOpen}
        step={topupStep}
        onClose={closeTopup}
        packs={topupPacks}
        selectedPackId={topupPackId}
        onSelectPack={setTopupPackId}
        onSubmit={submitTopup}
        starsBalance={starsBalance}
      />

      <Toast message={toast} />
    </div>
  );
}
