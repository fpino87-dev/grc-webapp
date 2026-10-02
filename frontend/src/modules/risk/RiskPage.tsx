import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { riskApi, type AssetType } from "../../api/endpoints/risk";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { scrollAndHighlight } from "../../lib/scrollAndHighlight";
import { CycleBar } from "./CycleBar";
import { RegisterTab } from "./RegisterTab";
import { MatrixTab } from "./MatrixTab";
import { CoverageTab } from "./CoverageTab";
import { PlanTab } from "./PlanTab";
import { AcceptancesTab } from "./AcceptancesTab";
import { CyclesTab } from "./CyclesTab";
import { SettingsTab } from "./SettingsTab";
import { RiskDrawer } from "./RiskDrawer";
import { NewRiskModal, type NewRiskPrefill } from "./NewRiskModal";

const TABS = ["register", "matrix", "coverage", "plan", "acceptances", "cycles", "settings"] as const;
type Tab = typeof TABS[number];

/** Registro corrente: id del sito, oppure null per il registro di gruppo. */
export type RegisterId = string | null;

export function RiskPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const requested = searchParams.get("tab");
  const tab: Tab = (TABS as readonly string[]).includes(requested ?? "") ? (requested as Tab) : "register";
  const setTab = (next: Tab) => {
    const params = new URLSearchParams(searchParams);
    params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });
  const [register, setRegister] = useState<RegisterId | undefined>(undefined);
  useEffect(() => {
    if (register !== undefined) return;
    if (selectedPlant?.id) setRegister(selectedPlant.id);
    else if (plants.length) setRegister(plants[0].id);
  }, [register, selectedPlant?.id, plants]);
  const registerId: RegisterId = register ?? null;
  const ready = register !== undefined;

  const { data: policy } = useQuery({
    queryKey: ["risk-policy", registerId],
    queryFn: () => riskApi.resolvedPolicy(registerId),
    enabled: ready,
    retry: false,
  });
  const { data: cycles = [] } = useQuery({
    queryKey: ["risk-cycles", registerId],
    queryFn: () => riskApi.cycles(registerId),
    enabled: ready,
    retry: false,
  });
  const openCycle = cycles.find(c => c.status === "in_corso" || c.status === "in_approvazione") ?? null;
  const approvedCycle = cycles.find(c => c.status === "approvato") ?? null;
  const evaluating = openCycle?.status === "in_corso";

  // Il registro di gruppo esiste solo se la policy lo prevede e l'utente ha scope org.
  const groupAvailable = !!policy?.group_register_enabled && !!policy?.user_org_scope;
  const canWrite = registerId !== null || !!policy?.user_org_scope;

  const [openRiskId, setOpenRiskId] = useState<string | null>(null);
  const [newRisk, setNewRisk] = useState<NewRiskPrefill | null>(null);

  // Deep link: dall'assistente, dal Reporting (state.openRiskId), dalla BIA
  // (state.newRiskFromProcess) o da un indirizzo /risk?id=.
  useEffect(() => {
    const state = location.state as { openRiskId?: string; newRiskFromProcess?: { process: string; plant: string } } | null;
    const fromQuery = searchParams.get("id");
    if (state?.openRiskId || fromQuery) {
      const id = state?.openRiskId ?? fromQuery!;
      setOpenRiskId(id);
      scrollAndHighlight(id);
    }
    if (state?.newRiskFromProcess) {
      setRegister(state.newRiskFromProcess.plant);
      setNewRisk({ critical_process: state.newRiskFromProcess.process });
    }
  }, [location.state, searchParams]);

  const registerLabel = useMemo(
    () => (registerId === null ? t("risk.page.group_register") : plants.find(p => p.id === registerId)?.name ?? ""),
    [registerId, plants, t],
  );

  const exportExcel = async () => {
    const resp = await riskApi.exportExcel(registerId);
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `risk_register_${registerId === null ? "gruppo" : plants.find(p => p.id === registerId)?.code ?? "sito"}.xlsx`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          {t("risk.page.title")}
          <ModuleHelp
            title={t("risk.help.title")}
            description={t("risk.help.description")}
            steps={[1, 2, 3, 4, 5, 6].map(n => t(`risk.help.steps.${n}`))}
            connections={[
              { module: "M00 Governance", relation: t("risk.help.connections.governance") },
              { module: "M03 Controlli", relation: t("risk.help.connections.controls") },
              { module: "M04 Asset", relation: t("risk.help.connections.assets") },
              { module: "M05 BIA", relation: t("risk.help.connections.bia") },
              { module: "M13 Riesame", relation: t("risk.help.connections.review") },
            ]}
            configNeeded={[t("risk.help.config_needed.1"), t("risk.help.config_needed.2")]}
          />
        </h2>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">{t("risk.page.register")}</label>
          <select
            value={registerId ?? "__group__"}
            onChange={e => setRegister(e.target.value === "__group__" ? null : e.target.value)}
            className="border rounded px-2 py-1.5 text-sm"
            aria-label={t("risk.page.register")}
          >
            {groupAvailable && <option value="__group__">{t("risk.page.group_register")}</option>}
            {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
          </select>
          <button onClick={exportExcel} disabled={!ready}
            className="px-3 py-1.5 border border-green-300 text-green-700 rounded text-sm hover:bg-green-50 disabled:opacity-50">
            ⬇ {t("risk.page.export")}
          </button>
          <button
            onClick={() => setNewRisk({})}
            disabled={!evaluating || !canWrite}
            title={!evaluating ? t("risk.page.new_needs_cycle") : undefined}
            className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            + {t("risk.page.new_risk")}
          </button>
        </div>
      </div>

      {ready && (
        <CycleBar
          registerId={registerId}
          registerLabel={registerLabel}
          openCycle={openCycle}
          approvedCycle={approvedCycle}
          hasLegacy={cycles.some(c => c.kind === "legacy")}
          canWrite={canWrite}
          orgScope={!!policy?.user_org_scope}
        />
      )}

      <div className="border-b border-gray-200 mb-4">
        <nav className="-mb-px flex flex-wrap gap-5" aria-label={t("risk.page.tabs_label")}>
          {TABS.map(key => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`whitespace-nowrap py-2 px-1 border-b-2 text-sm font-medium ${
                tab === key ? "border-primary-600 text-primary-700" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t(`risk.page.tabs.${key}`)}
            </button>
          ))}
        </nav>
      </div>

      {ready && tab === "register" && (
        <RegisterTab registerId={registerId} onOpen={setOpenRiskId} />
      )}
      {ready && tab === "matrix" && <MatrixTab registerId={registerId} onOpen={setOpenRiskId} />}
      {ready && tab === "coverage" && (
        <CoverageTab
          registerId={registerId}
          evaluating={evaluating && canWrite}
          onOpen={setOpenRiskId}
          onEvaluate={(asset_type: AssetType, threat: string) => setNewRisk({ asset_type, threat })}
        />
      )}
      {ready && tab === "plan" && <PlanTab registerId={registerId} onOpen={setOpenRiskId} />}
      {ready && tab === "acceptances" && <AcceptancesTab registerId={registerId} onOpen={setOpenRiskId} />}
      {ready && tab === "cycles" && <CyclesTab registerId={registerId} cycles={cycles} onOpen={setOpenRiskId} />}
      {ready && tab === "settings" && policy && (
        <SettingsTab registerId={registerId} policy={policy} plants={plants} />
      )}

      {openRiskId && (
        <RiskDrawer
          riskId={openRiskId}
          registerId={registerId}
          evaluating={evaluating}
          cycleKind={openCycle?.kind ?? null}
          canWrite={canWrite}
          orgScope={!!policy?.user_org_scope}
          onClose={() => setOpenRiskId(null)}
        />
      )}
      {newRisk && (
        <NewRiskModal
          registerId={registerId}
          plants={plants}
          prefill={newRisk}
          onClose={() => setNewRisk(null)}
          onCreated={id => { setNewRisk(null); setOpenRiskId(id); }}
        />
      )}
    </div>
  );
}
