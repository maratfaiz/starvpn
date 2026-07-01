/**
 * App root.
 * Initialises @tma.js/sdk, reads Telegram user data,
 * then renders the Dashboard.
 */

import { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";

export default function App() {
  const [tgUser, setTgUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      setTgUser(tg.initDataUnsafe?.user || null);
    }
    setReady(true);
  }, []);

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <span className="text-tg-hint text-sm animate-pulse">Загрузка...</span>
      </div>
    );
  }

  return <Dashboard user={tgUser} />;
}
