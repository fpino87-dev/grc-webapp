import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { plantsApi } from "../../api/endpoints/plants";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { riskApi, type RiskAssessment } from "../../api/endpoints/risk";
import { bcpApi } from "../../api/endpoints/bcp";
import { usersApi, type GrcUser } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";

type Step = 1 | 2 | 3 | 4;

interface WizardState {
  plantId: string;
  process: CriticalProcess | null;
  risk: RiskAssessment | null;
  bcpPlanId: string | null;
}

export function RiskContinuityWizard({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const currentUser = useAuthStore(s => s.user);
  const [step, setStep] = useState<Step>(1);
  const [state, setState] = useState<WizardState>({
    plantId: selectedPlant?.id ?? "",
    process: null,
    risk: null,
    bcpPlanId: null,
  });
  const [bcpCriticalProcessId, setBcpCriticalProcessId] = useState<string>("");
  const [creatingProcess, setCreatingProcess] = useState(false);
  const [processForm, setProcessForm] = useState<Partial<CriticalProcess>>({
    criticality: 3,
  });
  const [riskForm, setRiskForm] = useState<Partial<RiskAssessment>>({
    assessment_type: "IT",
    inherent_probability: null,
    inherent_impact: null,
    treatment: "mitigare",
  });
  const [bcpForm, setBcpForm] = useState<{
    title: string;
    version: string;
    rto_hours: string;
    rpo_hours: string;
    test_frequency_value: number;
    test_frequency_unit: "days" | "weeks" | "months" | "years";
  }>({
    title: "",
    version: "1.0",
    rto_hours: "",
    rpo_hours: "",
    test_frequency_value: 1,
    test_frequency_unit: "years",
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const { data: processesData } = useQuery({
    queryKey: ["bia-wizard-processes", state.plantId],
    queryFn: () => biaApi.list(state.plantId ? { plant: state.plantId, page_size: "200" } : {}),
    enabled: !!state.plantId,
    retry: false,
  });

  useEffect(() => {
    if (!currentUser?.id) return;
    setRiskForm(f => {
      if (f.owner != null) return f; // non sovrascrive una scelta manuale
      return { ...f, owner: currentUser.id };
    });
  }, [currentUser?.id]);

  // Quando l'utente seleziona un processo esistente (e non sta creando), precompilo i campi editabili.
  useEffect(() => {
    if (!state.process) return;
    if (creatingProcess) return;
    setProcessForm({
      name: state.process.name,
      criticality: state.process.criticality,
      downtime_cost_hour: state.process.downtime_cost_hour,
      mtpd_hours: state.process.mtpd_hours,
      mbco_pct: state.process.mbco_pct,
      rto_target_hours: state.process.rto_target_hours,
      rpo_target_hours: state.process.rpo_target_hours,
    });
  }, [state.process?.id, creatingProcess]);

  const createProcessMutation = useMutation({
    mutationFn: () => biaApi.create({ ...processForm, plant: state.plantId }),
    onSuccess: (proc) => {
      qc.invalidateQueries({ queryKey: ["bia"] });
      setState(s => ({ ...s, process: proc }));
      setBcpCriticalProcessId(proc.id);
      setCreatingProcess(false);
      setStep(2);
    },
  });

  const updateProcessMutation = useMutation({
    mutationFn: () => {
      if (!state.process) return Promise.reject(new Error(t("risk.no_process_selected")));
      return biaApi.update(state.process.id, {
        name: processForm.name ?? state.process.name,
        criticality: processForm.criticality ?? state.process.criticality,
        downtime_cost_hour: processForm.downtime_cost_hour ?? state.process.downtime_cost_hour,
        mtpd_hours: processForm.mtpd_hours ?? state.process.mtpd_hours,
        mbco_pct: processForm.mbco_pct ?? state.process.mbco_pct,
        rto_target_hours: processForm.rto_target_hours ?? state.process.rto_target_hours,
        rpo_target_hours: processForm.rpo_target_hours ?? state.process.rpo_target_hours,
      });
    },
    onSuccess: (proc) => {
      qc.invalidateQueries({ queryKey: ["bia"] });
      setState(s => ({ ...s, process: proc }));
      setBcpCriticalProcessId(proc.id);
      setStep(2);
    },
  });

  const createRiskMutation = useMutation({
    mutationFn: () =>
      riskApi.create({
        ...riskForm,
        plant: state.plantId,
        critical_process: state.process?.id,
        owner: riskForm.owner ?? currentUser?.id ?? null,
      }),
    onSuccess: (risk) => {
      qc.invalidateQueries({ queryKey: ["risk-assessments"] });
      setState(s => ({ ...s, risk }));
      setStep(3);
    },
  });

  const createBcpMutation = useMutation({
    mutationFn: () =>
      bcpApi.create({
        plant: state.plantId,
        title: bcpForm.title,
        version: bcpForm.version,
        rto_hours: bcpForm.rto_hours ? Number(bcpForm.rto_hours) : null,
        rpo_hours: bcpForm.rpo_hours ? Number(bcpForm.rpo_hours) : null,
        critical_process: bcpCriticalProcessId || state.process?.id || null,
        test_frequency_value: bcpForm.test_frequency_value,
        test_frequency_unit: bcpForm.test_frequency_unit,
      }),
    onSuccess: (plan) => {
      qc.invalidateQueries({ queryKey: ["bcp"] });
      setState(s => ({ ...s, bcpPlanId: plan.id }));
      setStep(4);
    },
  });

  const processes = processesData?.results ?? [];
  const selectedBcpProcess =
    processes.find(p => p.id === (bcpCriticalProcessId || state.process?.id || "")) ?? state.process;

  function resetAndClose() {
    setStep(1);
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[95vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{t("risk.wizard_title")}</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {t("risk.wizard_subtitle")}
            </p>
          </div>
          <button
            onClick={resetAndClose}
            className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100"
          >
            ×
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-6 pt-3 pb-2 border-b border-gray-100">
          <div className="flex items-center gap-4 text-xs font-medium text-gray-600">
            <div className={`flex items-center gap-2 ${step === 1 ? "text-primary-700" : step > 1 ? "text-green-700" : ""}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${
                step > 1 ? "bg-green-600 text-white" : step === 1 ? "bg-primary-600 text-white" : "bg-gray-200 text-gray-600"
              }`}>1</span>
              <span>{t("risk.wizard_step_bia")}</span>
            </div>
            <div className="h-px flex-1 bg-gray-200" />
            <div className={`flex items-center gap-2 ${step === 2 ? "text-primary-700" : step > 2 ? "text-green-700" : ""}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${
                step > 2 ? "bg-green-600 text-white" : step === 2 ? "bg-primary-600 text-white" : "bg-gray-200 text-gray-600"
              }`}>2</span>
              <span>{t("risk.wizard_step_risk")}</span>
            </div>
            <div className="h-px flex-1 bg-gray-200" />
            <div className={`flex items-center gap-2 ${step === 3 ? "text-primary-700" : step > 3 ? "text-green-700" : ""}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${
                step > 3 ? "bg-green-600 text-white" : step === 3 ? "bg-primary-600 text-white" : "bg-gray-200 text-gray-600"
              }`}>3</span>
              <span>{t("risk.wizard_step_bcp")}</span>
            </div>
          </div>
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {step === 1 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-gray-800 mb-2">1A. Sito e processo critico</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Sito *</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={state.plantId}
                      onChange={e => setState(s => ({ ...s, plantId: e.target.value, process: null }))}
                    >
                      <option value="">— seleziona —</option>
                      {plants?.map(p => (
                        <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                      ))}
                    </select>
                  </div>
                  {state.plantId && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Seleziona processo esistente</label>
                      <select
                        className="w-full border rounded px-3 py-2 text-sm"
                        value={state.process?.id ?? ""}
                        onChange={e => {
                          const proc = processes.find(p => p.id === e.target.value) ?? null;
                          setState(s => ({ ...s, process: proc }));
                          setBcpCriticalProcessId(proc?.id ?? "");
                        }}
                      >
                        <option value="">— nessun processo selezionato —</option>
                        {processes.map(p => (
                          <option key={p.id} value={p.id}>
                            {p.name} [criticità {p.criticality}]
                          </option>
                        ))}
                      </select>
                      <p className="text-[11px] text-gray-400 mt-1">
                        Puoi anche creare un nuovo processo nella colonna a destra.
                      </p>
                    </div>
                  )}

                  <div className="border border-gray-200 bg-white rounded-lg p-3">
                    <div className="text-[11px] font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                      Legenda sigle e criticità
                    </div>
                    <div className="space-y-1">
                      <div className="text-[11px] text-gray-600">
                        <strong>MTPD</strong> = ore massime di interruzione tollerabili
                      </div>
                      <div className="text-[11px] text-gray-600">
                        <strong>MBCO</strong> = % minima di continuità richiesta
                      </div>
                      <div className="text-[11px] text-gray-600">
                        <strong>RTO</strong> = ore per il ripristino
                      </div>
                      <div className="text-[11px] text-gray-600">
                        <strong>RPO</strong> = ore di perdita accettabile
                      </div>
                      <div className="pt-2 border-t border-gray-100 text-[11px] text-gray-600">
                        <strong>Criticità 1–5</strong>:
                        <span className="ml-1">1 bassa</span>, <span>3 media</span>, <span>5 critica</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-800">1B. Nuovo processo BIA</h4>
                  <label className="flex items-center gap-1 text-xs text-gray-600">
                    <input
                      type="checkbox"
                      className="accent-primary-600"
                      checked={creatingProcess}
                      onChange={e => setCreatingProcess(e.target.checked)}
                      disabled={!state.plantId}
                    />
                    <span>{t("risk.wizard_create_new")}</span>
                  </label>
                </div>
                {!state.plantId && (
                  <p className="text-xs text-gray-500">
                    Seleziona prima un sito per creare il processo.
                  </p>
                )}
                {state.plantId && creatingProcess && (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Nome processo *</label>
                      <input
                        className="w-full border rounded px-3 py-1.5 text-sm"
                        value={(processForm.name as string) ?? ""}
                        onChange={e => setProcessForm(f => ({ ...f, name: e.target.value }))}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Criticità (1-5)</label>
                        <select
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.criticality ?? 3}
                          onChange={e => setProcessForm(f => ({ ...f, criticality: Number(e.target.value) }))}
                        >
                          {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Costo downtime/h (€)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.downtime_cost_hour as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, downtime_cost_hour: e.target.value }))}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">MTPD (ore)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.mtpd_hours as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, mtpd_hours: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">MBCO (%)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.mbco_pct as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, mbco_pct: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">RTO target (ore)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.rto_target_hours as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, rto_target_hours: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">RPO target (ore)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.rpo_target_hours as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, rpo_target_hours: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                    </div>
                  </div>
                )}
                {state.process && !creatingProcess && (
                  <div className="mt-2 text-xs text-gray-600 bg-white border border-gray-200 rounded p-3 space-y-3">
                    <div className="font-semibold">Modifica processo selezionato</div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Nome processo *</label>
                      <input
                        className="w-full border rounded px-3 py-1.5 text-sm"
                        value={(processForm.name as string) ?? state.process.name ?? ""}
                        onChange={e => setProcessForm(f => ({ ...f, name: e.target.value }))}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Criticità (1-5)</label>
                        <select
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.criticality ?? state.process.criticality ?? 3}
                          onChange={e => setProcessForm(f => ({ ...f, criticality: Number(e.target.value) }))}
                        >
                          {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Costo downtime/h (€)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.downtime_cost_hour as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, downtime_cost_hour: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">MTPD (ore)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.mtpd_hours as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, mtpd_hours: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">MBCO (%)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.mbco_pct as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, mbco_pct: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">RTO target (ore)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.rto_target_hours as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, rto_target_hours: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">RPO target (ore)</label>
                        <input
                          type="number"
                          className="w-full border rounded px-3 py-1.5 text-sm"
                          value={processForm.rpo_target_hours as any ?? ""}
                          onChange={e => setProcessForm(f => ({ ...f, rpo_target_hours: e.target.value ? Number(e.target.value) : null }))}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 2 && state.process && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-800">2. Scenario di rischio collegato al processo</h4>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Nome scenario / rischio *</label>
                  <input
                    className="w-full border rounded px-3 py-1.5 text-sm"
                    value={riskForm.name as string ?? ""}
                    onChange={e => setRiskForm(f => ({ ...f, name: e.target.value }))}
                    placeholder={t("risk.scenario_placeholder")}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Tipo (IT/OT)</label>
                    <select
                      className="w-full border rounded px-3 py-1.5 text-sm"
                      value={riskForm.assessment_type ?? "IT"}
                      onChange={e => setRiskForm(f => ({ ...f, assessment_type: e.target.value as "IT" | "OT" }))}
                    >
                      <option value="IT">IT</option>
                      <option value="OT">OT</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Categoria minaccia</label>
                    <select
                      className="w-full border rounded px-3 py-1.5 text-sm"
                      value={riskForm.threat_category as string ?? ""}
                      onChange={e => setRiskForm(f => ({ ...f, threat_category: e.target.value }))}
                    >
                      <option value="">— seleziona —</option>
                      {["accesso_non_autorizzato","malware_ransomware","data_breach","phishing_social","guasto_hw_sw","disastro_naturale","errore_umano","attacco_supply_chain","ddos","insider_threat","furto_perdita","altro"].map(v => (
                        <option key={v} value={v}>{v}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Trattamento previsto</label>
                    <select
                      className="w-full border rounded px-3 py-1.5 text-sm"
                      value={riskForm.treatment ?? "mitigare"}
                      onChange={e => setRiskForm(f => ({ ...f, treatment: e.target.value }))}
                    >
                      <option value="mitigare">{t("risk.treatment_mitigare")}</option>
                      <option value="accettare">{t("risk.treatment_accettare")}</option>
                      <option value="trasferire">{t("risk.treatment_trasferire")}</option>
                      <option value="evitare">{t("risk.treatment_evitare")}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={(riskForm.owner as string | null) ?? ""}
                      onChange={e => setRiskForm(f => ({ ...f, owner: e.target.value || null }))}
                    >
                      <option value="">— seleziona —</option>
                      {(users as GrcUser[] | undefined)?.map(u => (
                        <option key={u.id} value={String(u.id)}>
                          {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="border border-orange-200 rounded-lg p-3 bg-orange-50/30">
                  <p className="text-xs font-medium text-orange-800 mb-2">Rischio inerente (prima dei controlli)</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Probabilità inerente *</label>
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={riskForm.inherent_probability as any ?? ""}
                        onChange={e => setRiskForm(f => ({ ...f, inherent_probability: e.target.value ? Number(e.target.value) : null }))}
                      >
                        <option value="">— seleziona —</option>
                        {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Impatto inerente *</label>
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={riskForm.inherent_impact as any ?? ""}
                        onChange={e => setRiskForm(f => ({ ...f, inherent_impact: e.target.value ? Number(e.target.value) : null }))}
                      >
                        <option value="">— seleziona —</option>
                        {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    </div>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-3">
                  <p className="text-xs font-medium text-gray-700 mb-2">Rischio residuo (P × I dopo i controlli)</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Probabilità *</label>
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={riskForm.probability as any ?? ""}
                        onChange={e => setRiskForm(f => ({ ...f, probability: e.target.value ? Number(e.target.value) : null }))}
                      >
                        <option value="">— seleziona —</option>
                        {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Impatto *</label>
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={riskForm.impact as any ?? ""}
                        onChange={e => setRiskForm(f => ({ ...f, impact: e.target.value ? Number(e.target.value) : null }))}
                      >
                        <option value="">— seleziona —</option>
                        {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Frequenza test BCP</label>
                  <select
                    className="w-full border rounded px-3 py-2 text-sm"
                    value={`${bcpForm.test_frequency_value}:${bcpForm.test_frequency_unit}`}
                    onChange={(e) => {
                      const [v, u] = e.target.value.split(":");
                      setBcpForm(f => ({
                        ...f,
                        test_frequency_value: Number(v),
                        test_frequency_unit: u as "days" | "weeks" | "months" | "years",
                      }));
                    }}
                  >
                    <option value="1:weeks">{t("common.freq_weekly")}</option>
                    <option value="1:months">{t("common.freq_monthly")}</option>
                    <option value="3:months">{t("common.freq_quarterly")}</option>
                    <option value="6:months">{t("common.freq_biannual")}</option>
                    <option value="1:years">{t("common.freq_annual")}</option>
                  </select>
                </div>
              </div>

              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 text-xs text-gray-700 space-y-2">
                <h4 className="text-sm font-semibold text-gray-800">Riepilogo BIA del processo</h4>
                <p className="font-medium">{state.process.name}</p>
                <p>Criticità: <strong>{state.process.criticality}</strong> / 5</p>
                <p>MTPD: <strong>{state.process.mtpd_hours ?? "—"} h</strong></p>
                <p>RTO target: <strong>{state.process.rto_target_hours ?? "—"} h</strong></p>
                <p>RPO target: <strong>{state.process.rpo_target_hours ?? "—"} h</strong></p>
                <p>Costo downtime/h: <strong>{state.process.downtime_cost_hour ?? "—"}</strong></p>
                <p className="text-[11px] text-gray-500 mt-2">
                  Lo score di rischio e l&apos;ALE verranno calcolati in base ai dati BIA quando completi l&apos;assessment.
                </p>
              </div>
            </div>
          )}

          {step === 3 && state.process && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-800">3. Piano BCP per il processo</h4>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Processo BIA da associare al BCP *</label>
                  <select
                    className="w-full border rounded px-3 py-2 text-sm"
                    value={bcpCriticalProcessId || state.process.id}
                    onChange={e => setBcpCriticalProcessId(e.target.value)}
                  >
                    {processes.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.name} [criticità {p.criticality}]
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Titolo piano *</label>
                  <input
                    className="w-full border rounded px-3 py-1.5 text-sm"
                    value={bcpForm.title}
                    onChange={e => setBcpForm(f => ({ ...f, title: e.target.value }))}
                    placeholder="es. BCP Produzione MES Plant A"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Versione</label>
                    <input
                      className="w-full border rounded px-3 py-1.5 text-sm"
                      value={bcpForm.version}
                      onChange={e => setBcpForm(f => ({ ...f, version: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">RTO piano (ore)</label>
                    <input
                      type="number"
                      className="w-full border rounded px-3 py-1.5 text-sm"
                      value={bcpForm.rto_hours}
                      onChange={e => setBcpForm(f => ({ ...f, rto_hours: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">RPO piano (ore)</label>
                    <input
                      type="number"
                      className="w-full border rounded px-3 py-1.5 text-sm"
                      value={bcpForm.rpo_hours}
                      onChange={e => setBcpForm(f => ({ ...f, rpo_hours: e.target.value }))}
                    />
                  </div>
                </div>
              </div>

              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 text-xs text-gray-700 space-y-2">
                <h4 className="text-sm font-semibold text-gray-800">Verifica coerenza con BIA</h4>
                <p><strong>Processo:</strong> {selectedBcpProcess?.name}</p>
                <p>MTPD: <strong>{selectedBcpProcess?.mtpd_hours ?? "—"} h</strong></p>
                <p>RTO target: <strong>{selectedBcpProcess?.rto_target_hours ?? "—"} h</strong></p>
                <p>
                  RTO piano inserito:{" "}
                  <strong>{bcpForm.rto_hours || "—"} h</strong>
                  {selectedBcpProcess?.rto_target_hours && bcpForm.rto_hours && Number(bcpForm.rto_hours) > (selectedBcpProcess?.rto_target_hours ?? 0) && (
                    <span className="ml-1 text-red-600">
                      (⚠ supera il target BIA)
                    </span>
                  )}
                </p>
                <p className="text-[11px] text-gray-500 mt-2">
                  Se il RTO del piano supera MTPD/RTO target, verranno generati avvisi e PDCA quando registri i test BCP.
                </p>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-gray-800">Scenario creato</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-700">
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                  <div className="font-semibold text-gray-800 mb-1">Processo BIA</div>
                  {selectedBcpProcess ? (
                    <>
                      <p>{selectedBcpProcess.name}</p>
                      <p className="text-gray-500 mt-1">
                        Criticità {selectedBcpProcess.criticality}/5 • MTPD {selectedBcpProcess.mtpd_hours ?? "—"}h • RTO {selectedBcpProcess.rto_target_hours ?? "—"}h
                      </p>
                    </>
                  ) : (
                    <p className="text-gray-400">Nessun processo collegato</p>
                  )}
                </div>
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                  <div className="font-semibold text-gray-800 mb-1">Scenario di rischio</div>
                  {state.risk ? (
                    <>
                      <p>{state.risk.name || "Scenario senza nome"}</p>
                      <p className="text-gray-500 mt-1">
                        Tipo {state.risk.assessment_type} • Score {state.risk.score ?? "—"}
                      </p>
                    </>
                  ) : (
                    <p className="text-gray-400">Nessun rischio creato</p>
                  )}
                </div>
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                  <div className="font-semibold text-gray-800 mb-1">Piano BCP</div>
                  {state.bcpPlanId ? (
                    <p>Piano creato e collegato al processo.</p>
                  ) : (
                    <p className="text-gray-400">Nessun piano creato</p>
                  )}
                </div>
              </div>
              <p className="text-[11px] text-gray-500">
                Puoi ora rifinire i dettagli nelle sezioni BIA, Risk Assessment e BCP del menu principale.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center px-6 py-3 border-t border-gray-100">
          <button
            onClick={resetAndClose}
            className="px-3 py-1.5 text-xs text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            {t("common.close")}
          </button>
          <div className="flex gap-2">
            {step > 1 && step < 4 && (
              <button
                onClick={() => setStep((s) => (s - 1) as Step)}
                className="px-3 py-1.5 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              >
                {t("actions.back")}
              </button>
            )}
            {step === 1 && (
              <button
                disabled={
                  !state.plantId
                  || (!state.process && !creatingProcess)
                  || (creatingProcess && !processForm.name)
                }
                onClick={() => {
                  if (creatingProcess) {
                    createProcessMutation.mutate();
                  } else if (state.process) {
                    updateProcessMutation.mutate();
                  }
                }}
                className="px-4 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {t("risk.wizard_continue_risk")}
              </button>
            )}
            {step === 2 && (
              <button
                disabled={
                  !riskForm.name ||
                  !riskForm.threat_category ||
                  riskForm.inherent_probability == null ||
                  riskForm.inherent_impact == null ||
                  !riskForm.probability ||
                  !riskForm.impact
                }
                onClick={() => createRiskMutation.mutate()}
                className="px-4 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {t("risk.wizard_save_risk_continue")}
              </button>
            )}
            {step === 3 && (
              <button
                disabled={!bcpForm.title}
                onClick={() => createBcpMutation.mutate()}
                className="px-4 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {t("risk.wizard_create_bcp")}
              </button>
            )}
            {step === 4 && (
              <button
                onClick={resetAndClose}
                className="px-4 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
              >
                {t("common.finish")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

