import { useState, useRef, useEffect } from "react";
import { useAuthStore } from "../../store/auth";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { plantsApi } from "../../api/endpoints/plants";
import { notificationsApi } from "../../api/endpoints/notifications";
import i18n from "../../i18n";
import { useTranslation } from "react-i18next";
import { ManualDrawer } from "../ui/ManualDrawer";

function NotificationBell() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data: subs = [] } = useQuery({
    queryKey: ["notification-subscriptions"],
    queryFn: () => notificationsApi.subscriptions(),
    retry: false,
  });

  const enabledCount = subs.filter(s => s.enabled).length;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="relative text-gray-500 hover:text-gray-700 p-1 rounded transition-colors"
        title={t("topbar.notifications.title")}
      >
        <span className="text-lg">🔔</span>
        {enabledCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center leading-none">
            {enabledCount > 9 ? "9+" : enabledCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-800">{t("topbar.notifications.title")}</p>
          </div>
          {subs.length === 0 ? (
            <p className="px-4 py-6 text-sm text-gray-400 text-center">{t("topbar.notifications.empty")}</p>
          ) : (
            <div className="max-h-64 overflow-y-auto py-1">
              {subs.map(s => (
                <div key={s.id} className="px-4 py-2 flex items-center justify-between hover:bg-gray-50">
                  <div>
                    <p className="text-sm text-gray-700">{s.event_type}</p>
                    <p className="text-xs text-gray-400">{s.channel}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${s.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {s.enabled ? t("topbar.notifications.enabled") : t("topbar.notifications.disabled")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function Topbar() {
  const { t } = useTranslation();
  const { user, selectedPlant, setPlant, logout } = useAuthStore();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [lang, setLang] = useState<string>(i18n.language || localStorage.getItem("grc_lang") || "it");
  const [openManual, setOpenManual] = useState<"utente" | "tecnico" | null>(null);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function handleLanguageChange(next: string) {
    setLang(next);
    i18n.changeLanguage(next);
    localStorage.setItem("grc_lang", next);
  }

  return (
    <>
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* Plant selector */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen(o => !o)}
          className="flex items-center gap-1.5 text-sm hover:bg-gray-50 px-2 py-1 rounded transition-colors"
        >
          {selectedPlant?.id ? (
            <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-medium">
              {selectedPlant.code} — {selectedPlant.name}
            </span>
          ) : (
            <span className="text-gray-400 italic">{t("topbar.plant.none_selected")}</span>
          )}
          <span className="text-gray-400 text-xs">▾</span>
        </button>

        {dropdownOpen && (
          <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1">
            <button
              onClick={() => { setPlant({ id: "", code: "", name: "" }); setDropdownOpen(false); }}
              className="w-full text-left px-4 py-2 text-sm text-gray-500 hover:bg-gray-50 italic"
            >
              {t("topbar.plant.all")}
            </button>
            <div className="border-t border-gray-100 my-1" />
            {(plants ?? []).map(p => (
              <button
                key={p.id}
                onClick={() => { setPlant({ id: p.id, code: p.code, name: p.name }); setDropdownOpen(false); }}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center justify-between ${
                  selectedPlant?.id === p.id ? "bg-blue-50 text-blue-800 font-medium" : "text-gray-700"
                }`}
              >
                <span>{p.name}</span>
                <span className="text-xs text-gray-400 font-mono">{p.code}</span>
              </button>
            ))}
            {(plants ?? []).length === 0 && (
              <p className="px-4 py-2 text-sm text-gray-400">{t("topbar.plant.none_configured")}</p>
            )}
          </div>
        )}
      </div>

      {/* Right side: language, manuals, notifications, user info, logout */}
      <div className="flex items-center gap-4">
        {/* Language switcher */}
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <span className="hidden sm:inline text-gray-400">{t("topbar.language.label")}</span>
          <div className="inline-flex items-center gap-1 bg-gray-100 rounded-full px-1 py-0.5">
            {["it", "en", "fr", "pl", "tr"].map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => handleLanguageChange(code)}
                className={`px-1.5 py-0.5 rounded-full uppercase ${
                  lang === code
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-800"
                } text-[11px]`}
              >
                {code}
              </button>
            ))}
          </div>
        </div>

        {/* Manual buttons */}
        <div className="flex items-center gap-1 border-l border-gray-200 pl-4">
          <button
            onClick={() => setOpenManual("utente")}
            className="text-gray-400 hover:text-blue-600 transition-colors p-1 rounded text-base"
            title="Manuale Utente"
          >
            📖
          </button>
          <button
            onClick={() => setOpenManual("tecnico")}
            className="text-gray-400 hover:text-blue-600 transition-colors p-1 rounded text-base"
            title="Manuale Tecnico"
          >
            🔧
          </button>
        </div>

        <NotificationBell />
        {user && (
          <span className="text-sm text-gray-700">
            {user.email}
            <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
              {user.role}
            </span>
          </span>
        )}
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-600 transition-colors"
        >
          {t("topbar.logout")}
        </button>
      </div>
    </header>

      {openManual && (
        <ManualDrawer type={openManual} onClose={() => setOpenManual(null)} />
      )}
    </>
  );
}
