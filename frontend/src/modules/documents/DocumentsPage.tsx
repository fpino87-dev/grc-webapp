import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { scrollAndHighlight } from "../../lib/scrollAndHighlight";
import { TabDocumenti } from "./TabDocumenti";
import { TabNda } from "./TabNda";
import { TabEvidenze } from "./TabEvidenze";
import { useTranslation } from "react-i18next";

type MainTab = "documenti" | "nda" | "evidenze";

export function DocumentsPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const [mainTab, setMainTab] = useState<MainTab>("documenti");

  // Deep-link dal govrico Assistant: forziamo tab "documenti" e scrolliamo alla riga.
  useEffect(() => {
    const state = location.state as { openDocumentId?: string } | null;
    if (state?.openDocumentId) {
      setMainTab("documenti");
      scrollAndHighlight(state.openDocumentId);
    }
  }, [location.state]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">{t("documents.title")}</h2>

      {/* Tab principali */}
      <div className="flex gap-1 mb-5 border-b border-gray-200">
        <button
          onClick={() => setMainTab("documenti")}
          className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px ${
            mainTab === "documenti"
              ? "border-b-2 border-primary-600 text-primary-700 bg-primary-50 rounded-t"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          📄 {t("documents.tabs.documents")}
        </button>
        <button
          onClick={() => setMainTab("nda")}
          className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px ${
            mainTab === "nda"
              ? "border-b-2 border-amber-600 text-amber-700 bg-amber-50 rounded-t"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          📝 {t("documents.tabs.nda")}
        </button>
        <button
          onClick={() => setMainTab("evidenze")}
          className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px ${
            mainTab === "evidenze"
              ? "border-b-2 border-green-600 text-green-700 bg-green-50 rounded-t"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          🏆 {t("documents.tabs.evidences")}
        </button>
      </div>

      {mainTab === "documenti" && <TabDocumenti />}
      {mainTab === "nda" && <TabNda />}
      {mainTab === "evidenze" && <TabEvidenze />}
    </div>
  );
}
