import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { plantsApi, type Plant } from "../../api/endpoints/plants";
import { controlsApi } from "../../api/endpoints/controls";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";

const COUNTRIES = ["IT", "DE", "FR", "PL", "TR", "ES", "UK", "US", "RO", "CZ"];

function EditPlantModal({ plant, onClose }: { plant: Plant; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Plant>>({
    name: plant.name,
    country: plant.country,
    nis2_scope: plant.nis2_scope,
    status: plant.status,
    has_ot: plant.has_ot,
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: Partial<Plant>) => plantsApi.update(plant.id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["plants"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.error || e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore"),
  });

  function set(field: string, value: unknown) {
    setForm(f => ({ ...f, [field]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-1">{t("plants.edit.title")}</h3>
        <p className="text-xs text-gray-400 mb-4 font-mono">{plant.code}</p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
            <input value={form.name ?? ""} onChange={e => set("name", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.country")}</label>
              <select value={form.country ?? ""} onChange={e => set("country", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm">
                {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.status")}</label>
              <select value={form.status ?? ""} onChange={e => set("status", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="attivo">{t("status.attivo")}</option>
                <option value="in_dismissione">{t("status.in_dismissione")}</option>
                <option value="chiuso">{t("status.chiuso")}</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_scope")}</label>
            <select value={form.nis2_scope ?? ""} onChange={e => set("nis2_scope", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm">
              <option value="non_soggetto">{t("status.non_soggetto")}</option>
              <option value="importante">{t("status.importante")}</option>
              <option value="essenziale">{t("status.essenziale")}</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="edit_has_ot" checked={!!form.has_ot}
              onChange={e => set("has_ot", e.target.checked)} className="rounded" />
            <label htmlFor="edit_has_ot" className="text-sm text-gray-700">{t("plants.fields.has_ot")}</label>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

const EMPTY: Partial<Plant> = {
  code: "", name: "", country: "IT",
  nis2_scope: "non_soggetto", status: "attivo", has_ot: false,
};

function PlantModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Plant>>(EMPTY);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: plantsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["plants"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore durante il salvataggio"),
  });

  function set(field: string, value: unknown) {
    setForm(f => ({ ...f, [field]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("plants.new.title")}</h3>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.code")} *</label>
              <input value={form.code} onChange={e => set("code", e.target.value.toUpperCase())}
                className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder={t("plants.placeholders.code")} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.country")}</label>
              <input value={form.country} onChange={e => set("country", e.target.value.toUpperCase())}
                maxLength={2} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("plants.placeholders.country")} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
            <input value={form.name} onChange={e => set("name", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm" placeholder={t("plants.placeholders.name")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.status")}</label>
              <select value={form.status} onChange={e => set("status", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="attivo">{t("status.attivo")}</option>
                <option value="in_dismissione">{t("status.in_dismissione")}</option>
                <option value="chiuso">{t("status.chiuso")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_scope")}</label>
              <select value={form.nis2_scope} onChange={e => set("nis2_scope", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="non_soggetto">{t("status.non_soggetto")}</option>
                <option value="importante">{t("status.importante")}</option>
                <option value="essenziale">{t("status.essenziale")}</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="has_ot" checked={!!form.has_ot}
              onChange={e => set("has_ot", e.target.checked)} className="rounded" />
            <label htmlFor="has_ot" className="text-sm text-gray-700">{t("plants.fields.has_ot")}</label>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button onClick={() => mutation.mutate(form)} disabled={mutation.isPending || !form.code || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? t("common.saving") : t("plants.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// Raggruppa TISAX_L2 e TISAX_L3 come voce unica "TISAX"
type FwGroup = { key: string; label: string; isTisax: boolean; ids: Record<string, string> };

function buildGroups(frameworks: { id: string; code: string; name: string }[], assignedCodes: Set<string>): FwGroup[] {
  const groups: FwGroup[] = [];
  const tisaxL2 = frameworks.find(f => f.code === "TISAX_L2");
  const tisaxL3 = frameworks.find(f => f.code === "TISAX_L3");
  const tisaxBothAssigned = assignedCodes.has("TISAX_L2") && assignedCodes.has("TISAX_L3");
  if ((tisaxL2 || tisaxL3) && !tisaxBothAssigned) {
    groups.push({ key: "TISAX", label: "TISAX — VDA ISA 6.0", isTisax: true, ids: { L2: tisaxL2?.id ?? "", L3: tisaxL3?.id ?? "" } });
  }
  for (const f of frameworks) {
    if (f.code.startsWith("TISAX")) continue;
    if (assignedCodes.has(f.code)) continue;
    groups.push({ key: f.id, label: `${f.code} — ${f.name}`, isTisax: false, ids: { single: f.id } });
  }
  return groups;
}

function FrameworkPanel({ plant, onClose }: { plant: Plant; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  // "TISAX" is the virtual key for grouped TISAX entry; otherwise it's the framework id
  const [selectedKey, setSelectedKey] = useState("");
  const [tisaxLevel, setTisaxLevel] = useState<"L2" | "L3">("L2");
  const [nisLevel, setNisLevel] = useState<string>(plant.nis2_scope !== "non_soggetto" ? plant.nis2_scope : "importante");
  const [genericLevel, setGenericLevel] = useState("base");
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);
  const [error, setError] = useState("");

  const { data: assigned = [] } = useQuery({
    queryKey: ["plant-frameworks", plant.id],
    queryFn: () => plantsApi.plantFrameworks(plant.id),
  });

  const { data: frameworks = [] } = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => controlsApi.frameworks(),
  });

  const assignMutation = useMutation({
    mutationFn: async () => {
      if (selectedKey === "TISAX") {
        const tisaxL2Id = frameworks.find(f => f.code === "TISAX_L2")?.id;
        const tisaxL3Id = frameworks.find(f => f.code === "TISAX_L3")?.id;
        const assignedCodes = new Set(assigned.map(a => a.framework_code));
        if (tisaxLevel === "L2") {
          if (!assignedCodes.has("TISAX_L2") && tisaxL2Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL2Id, level: "AL2" });
        } else {
          // L3 = L2 + L3
          if (!assignedCodes.has("TISAX_L2") && tisaxL2Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL2Id, level: "AL2" });
          if (!assignedCodes.has("TISAX_L3") && tisaxL3Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL3Id, level: "AL3" });
        }
      } else {
        const isNis = frameworks.find(f => f.id === selectedKey)?.code.startsWith("NIS2");
        const level = isNis ? nisLevel : genericLevel;
        await plantsApi.assignFramework({ plant: plant.id, framework: selectedKey, level });
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plant-frameworks", plant.id] });
      qc.invalidateQueries({ queryKey: ["controls"] });
      setSelectedKey("");
      setError("");
    },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore"),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => plantsApi.toggleFramework(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plant-frameworks", plant.id] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => plantsApi.removeFramework(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plant-frameworks", plant.id] });
      qc.invalidateQueries({ queryKey: ["controls"] });
      setConfirmRemove(null);
    },
  });

  const assignedCodes = new Set(assigned.map(a => a.framework_code));
  const groups = buildGroups(frameworks, assignedCodes);
  const selectedIsNis = selectedKey !== "TISAX" && frameworks.find(f => f.id === selectedKey)?.code.startsWith("NIS2");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{t("plants.frameworks.title")}</h3>
            <p className="text-xs text-gray-400 mt-0.5">{plant.code} — {plant.name}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        {/* Assigned list */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
          {assigned.length === 0 ? (
            <p className="text-sm text-gray-400 italic">{t("plants.frameworks.empty")}</p>
          ) : assigned.map(pf => (
            <div key={pf.id} className="rounded-lg border border-gray-200 px-4 py-3">
              {confirmRemove === pf.id ? (
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-red-700">
                    {t("plants.frameworks.remove_confirm", { code: pf.framework_code })}
                  </p>
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => setConfirmRemove(null)} className="text-xs border rounded px-2 py-1 text-gray-600 hover:bg-gray-50">
                      {t("actions.cancel")}
                    </button>
                    <button onClick={() => removeMutation.mutate(pf.id)} disabled={removeMutation.isPending}
                      className="text-xs bg-red-600 text-white rounded px-2 py-1 hover:bg-red-700 disabled:opacity-50">
                      {removeMutation.isPending ? "..." : t("actions.delete")}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-bold text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded">{pf.framework_code}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${pf.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {pf.active ? t("common.enabled") : t("common.disabled")}
                      </span>
                      <span className="text-xs text-gray-400">{t("plants.frameworks.level", { level: pf.level })}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 leading-snug">{pf.framework_name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{t("plants.frameworks.active_from", { date: pf.active_from })}</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => toggleMutation.mutate(pf.id)} disabled={toggleMutation.isPending}
                      className="text-xs text-primary-600 hover:underline">
                      {pf.active ? t("plants.frameworks.deactivate") : t("plants.frameworks.activate")}
                    </button>
                    <button onClick={() => setConfirmRemove(pf.id)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline">
                      {t("actions.delete")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Assign footer */}
        {groups.length > 0 && (
          <div className="border-t border-gray-100 px-6 py-4 shrink-0 space-y-3">
            <p className="text-sm font-medium text-gray-700">{t("plants.frameworks.assign_new")}</p>

            {/* Framework selector */}
            <select
              value={selectedKey}
              onChange={e => { setSelectedKey(e.target.value); setError(""); }}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">{t("plants.frameworks.select")}</option>
              {groups.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
            </select>

            {/* TISAX sub-level */}
            {selectedKey === "TISAX" && (
              <div className="space-y-2">
                <div className="flex gap-3">
                  {(["L2", "L3"] as const).map(l => (
                    <label key={l} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${tisaxLevel === l ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}>
                      <input type="radio" name="tisax_level" value={l} checked={tisaxLevel === l} onChange={() => setTisaxLevel(l)} className="mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{t("plants.frameworks.tisax.assessment_level", { level: l })}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {l === "L2" ? t("plants.frameworks.tisax.l2_hint") : t("plants.frameworks.tisax.l3_hint")}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
                {tisaxLevel === "L3" && (
                  <p className="text-xs text-blue-600 bg-blue-50 rounded px-2 py-1.5">
                    {t("plants.frameworks.tisax.l3_notice", {
                      l2: frameworks.find(f => f.code === "TISAX_L2") ? "40" : "0",
                      l3: frameworks.find(f => f.code === "TISAX_L3") ? "28" : "0",
                      total: "68",
                    })}
                  </p>
                )}
              </div>
            )}

            {/* NIS2 level */}
            {selectedIsNis && (
              <div className="space-y-1.5">
                <div className="flex gap-3">
                  {[
                    { v: "essenziale", label: t("status.essenziale"), hint: t("plants.frameworks.nis2.essential_hint") },
                    { v: "importante", label: t("status.importante"),  hint: t("plants.frameworks.nis2.important_hint") },
                  ].map(o => (
                    <label key={o.v} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${nisLevel === o.v ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}>
                      <input type="radio" name="nis_level" value={o.v} checked={nisLevel === o.v} onChange={() => setNisLevel(o.v)} className="mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{o.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{o.hint}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Generic level (ISO etc.) */}
            {selectedKey && selectedKey !== "TISAX" && !selectedIsNis && (
              <select value={genericLevel} onChange={e => setGenericLevel(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500">
                <option value="base">{t("plants.frameworks.generic.base")}</option>
                <option value="avanzato">{t("plants.frameworks.generic.advanced")}</option>
                <option value="completo">{t("plants.frameworks.generic.complete")}</option>
              </select>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}

            {selectedKey && (
              <button
                onClick={() => assignMutation.mutate()}
                disabled={assignMutation.isPending}
                className="w-full py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
              >
                {assignMutation.isPending ? t("plants.frameworks.assigning") : t("plants.frameworks.assign")}
              </button>
            )}
            <p className="text-xs text-gray-400">{t("plants.frameworks.assign_help")}</p>
          </div>
        )}

        {groups.length === 0 && assigned.length > 0 && (
          <div className="border-t border-gray-100 px-6 py-3 shrink-0">
            <p className="text-xs text-gray-400">{t("plants.frameworks.all_assigned")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export function PlantsList() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const [editPlant, setEditPlant] = useState<Plant | null>(null);
  const [frameworkPlant, setFrameworkPlant] = useState<Plant | null>(null);
  const { data: plants, isLoading } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const { setPlant } = useAuthStore();

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("plants.title")}</h2>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          {t("plants.new.open")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : !plants?.length ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">{t("plants.empty")}</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">
              {t("plants.new.first")}
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.code")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.country")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.nis2")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.ot")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {plants.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs font-bold text-gray-700">{p.code}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{p.name}</td>
                  <td className="px-4 py-3 text-gray-500 uppercase text-xs">{p.country}</td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3">
                    {p.nis2_scope !== "non_soggetto"
                      ? <StatusBadge status={p.nis2_scope} />
                      : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {p.has_ot
                      ? <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">OT</span>
                      : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => setEditPlant(p)}
                        className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded px-1.5 py-0.5 hover:bg-gray-50"
                        title={t("plants.actions.edit_title")}>✏</button>
                      <button onClick={() => setFrameworkPlant(p)}
                        className="text-xs text-indigo-600 hover:underline">
                        {t("plants.actions.frameworks")}
                      </button>
                      <button onClick={() => setPlant({ id: p.id, code: p.code, name: p.name })}
                        className="text-xs text-primary-600 hover:underline">
                        {t("plants.actions.select")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <PlantModal onClose={() => setShowNew(false)} />}
      {editPlant && <EditPlantModal plant={editPlant} onClose={() => setEditPlant(null)} />}
      {frameworkPlant && <FrameworkPanel plant={frameworkPlant} onClose={() => setFrameworkPlant(null)} />}
    </div>
  );
}
