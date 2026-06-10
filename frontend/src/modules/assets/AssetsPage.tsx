import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { plantsApi } from "../../api/endpoints/plants";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { ITTab } from "./ITTab";
import { OTTab } from "./OTTab";
import { SWTab } from "./SWTab";
import { NewAssetModal } from "./NewAssetModal";
import { NewAssetModalSW } from "./AssetSwModals";
import { useTranslation } from "react-i18next";

export function AssetsPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"IT" | "OT" | "SW">("IT");
  const [search, setSearch] = useState("");
  const [showNew, setShowNew] = useState(false);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Asset IT/OT/SW
          <ModuleHelp
            title={t("assets.help.title")}
            description={t("assets.help.description")}
            steps={[
              t("assets.help.steps.1"),
              t("assets.help.steps.2"),
              t("assets.help.steps.3"),
              t("assets.help.steps.4"),
              t("assets.help.steps.5"),
            ]}
            connections={[
              { module: "M05 BIA", relation: t("assets.help.connections.bia") },
              { module: "M06 Risk", relation: t("assets.help.connections.risk") },
              { module: "M16 BCP", relation: t("assets.help.connections.bcp") },
            ]}
            configNeeded={[
              t("assets.help.config_needed.1"),
              t("assets.help.config_needed.2"),
              t("assets.help.config_needed.3"),
            ]}
          />
        </h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + {t("assets.new_asset_btn", { type: activeTab })}
        </button>

      </div>

      <div className="mb-4 flex items-center gap-4">
        <div className="flex border-b border-gray-200">
          {(["IT", "OT", "SW"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setSearch(""); }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab === "SW" ? "Software (ASL)" : `Asset ${tab}`}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder={t("assets.search_placeholder")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto border rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {activeTab === "IT" && <ITTab search={search} />}
        {activeTab === "OT" && <OTTab search={search} />}
        {activeTab === "SW" && <SWTab search={search} />}
      </div>

      {showNew && plants && activeTab !== "SW" && (
        <NewAssetModal assetType={activeTab} plants={plants} onClose={() => setShowNew(false)} />
      )}
      {showNew && plants && activeTab === "SW" && (
        <NewAssetModalSW plants={plants} onClose={() => setShowNew(false)} />
      )}
    </div>
  );
}
