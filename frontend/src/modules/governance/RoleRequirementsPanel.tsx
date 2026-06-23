import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { governanceApi, type RoleRequirement } from "../../api/endpoints/governance";

const ROLE_OPTIONS = [
  "ciso", "compliance_officer", "risk_manager", "internal_auditor", "external_auditor",
  "plant_manager", "control_owner", "plant_security_officer", "nis2_contact", "dpo",
  "isms_manager", "comitato_membro", "bu_referente", "raci_responsible", "raci_accountable",
];

export function RoleRequirementsPanel() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Partial<RoleRequirement>>({
    role: "ciso",
    scope_level: "org",
    applies_to: "all",
    org_covers_sites: false,
    enabled: true,
    framework_refs: [],
  });
  const [error, setError] = useState("");

  const { data: requirements, isLoading } = useQuery({
    queryKey: ["governance-role-requirements"],
    queryFn: () => governanceApi.listRoleRequirements(),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["governance-role-requirements"] });
    qc.invalidateQueries({ queryKey: ["governance-coverage-matrix"] });
    qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
  };

  const createMut = useMutation({
    mutationFn: () => governanceApi.createRoleRequirement(form),
    onSuccess: () => { invalidate(); setShowForm(false); setError(""); },
    onError: (e: any) => setError(JSON.stringify(e?.response?.data) || t("common.error")),
  });
  const toggleMut = useMutation({
    mutationFn: (r: RoleRequirement) => governanceApi.updateRoleRequirement(r.id, { enabled: !r.enabled }),
    onSuccess: invalidate,
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => governanceApi.deleteRoleRequirement(id),
    onSuccess: invalidate,
  });

  function roleLabel(role: string) {
    return t(`governance.roles.${role}`, { defaultValue: role });
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">{t("governance.requirements.title")}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{t("governance.requirements.subtitle")}</p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
        >
          {t("governance.requirements.add")}
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded p-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("governance.requirements.role")}</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("governance.requirements.scope_level")}</label>
            <select
              value={form.scope_level}
              onChange={(e) => setForm({ ...form, scope_level: e.target.value as "org" | "plant" })}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="org">{t("governance.requirements.scope_level_org")}</option>
              <option value="plant">{t("governance.requirements.scope_level_plant")}</option>
            </select>
          </div>
          {form.scope_level === "plant" && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t("governance.requirements.applies_to")}</label>
                <select
                  value={form.applies_to}
                  onChange={(e) => setForm({ ...form, applies_to: e.target.value as "all" | "nis2_only" })}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="all">{t("governance.requirements.applies_all")}</option>
                  <option value="nis2_only">{t("governance.requirements.applies_nis2")}</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700 sm:mt-6">
                <input
                  type="checkbox"
                  checked={!!form.org_covers_sites}
                  onChange={(e) => setForm({ ...form, org_covers_sites: e.target.checked })}
                />
                {t("governance.requirements.org_covers_sites")}
              </label>
            </>
          )}
          <div className="sm:col-span-2 flex justify-end gap-2">
            {error && <p className="text-xs text-red-600 self-center">{error}</p>}
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
            <button
              onClick={() => createMut.mutate()}
              disabled={createMut.isPending}
              className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t("governance.requirements.save")}
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400">{t("common.loading")}</p>
      ) : !requirements?.length ? (
        <p className="text-sm text-gray-400 italic">{t("governance.requirements.empty")}</p>
      ) : (
        <div className="space-y-1">
          {requirements.map((r) => (
            <div key={r.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0 gap-2">
              <div className="min-w-0">
                <span className={`text-sm font-medium ${r.enabled ? "text-gray-800" : "text-gray-400 line-through"}`}>
                  {roleLabel(r.role)}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {r.scope_level === "org"
                    ? t("governance.requirements.scope_level_org")
                    : `${t("governance.requirements.scope_level_plant")} · ${r.applies_to === "nis2_only" ? t("governance.requirements.applies_nis2") : t("governance.requirements.applies_all")}${r.org_covers_sites ? " · " + t("governance.requirements.org_covers_sites") : ""}`}
                </span>
              </div>
              <div className="flex gap-1 shrink-0">
                <button
                  onClick={() => toggleMut.mutate(r)}
                  className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
                >
                  {r.enabled ? t("governance.requirements.disable") : t("governance.requirements.enable")}
                </button>
                <button
                  onClick={() => { if (window.confirm(t("governance.requirements.delete_confirm"))) deleteMut.mutate(r.id); }}
                  className="text-xs px-2 py-1 bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100"
                >
                  {t("actions.delete")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
