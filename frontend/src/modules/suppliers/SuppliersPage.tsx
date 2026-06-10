import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { SupplierEvaluationSettingsPage } from "../settings/SupplierEvaluationSettingsPage";
import { scrollAndHighlight } from "../../lib/scrollAndHighlight";
import { FornitoriTab } from "./FornitoriTab";
import { QuestionariTab } from "./QuestionariTab";
import { TemplateTab } from "./TemplateTab";
import { NdaTab } from "./NdaTab";
import { useTranslation } from "react-i18next";

type Tab = "fornitori" | "questionari" | "template" | "nda" | "impostazioni";

export function SuppliersPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const [tab, setTab] = useState<Tab>("fornitori");

  // Deep-link dal govrico Assistant: forziamo tab "fornitori" e scrolliamo alla riga.
  useEffect(() => {
    const state = location.state as { openSupplierId?: string } | null;
    if (state?.openSupplierId) {
      setTab("fornitori");
      scrollAndHighlight(state.openSupplierId);
    }
  }, [location.state]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "fornitori",    label: t("suppliers.tabs.suppliers") },
    { id: "questionari",  label: t("suppliers.tabs.questionnaires") },
    { id: "template",     label: t("suppliers.tabs.templates") },
    { id: "nda",          label: t("suppliers.tabs.nda_status") },
    { id: "impostazioni", label: t("suppliers.tabs.settings") },
  ];

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">{t("suppliers.page_title")}</h2>

      {/* Tab bar */}
      <div className="flex border-b border-gray-200 mb-5">
        {tabs.map(tb => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === tb.id
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {tb.label}
          </button>
        ))}
      </div>

      {tab === "fornitori"    && <FornitoriTab />}
      {tab === "questionari"  && <QuestionariTab />}
      {tab === "template"     && <TemplateTab />}
      {tab === "nda"          && <NdaTab />}
      {tab === "impostazioni" && <SupplierEvaluationSettingsPage />}
    </div>
  );
}
