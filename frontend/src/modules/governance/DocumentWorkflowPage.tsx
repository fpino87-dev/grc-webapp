import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { governanceApi, type DocumentWorkflowPolicy } from "../../api/endpoints/governance";
import { plantsApi } from "../../api/endpoints/plants";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

const DOCUMENT_TYPE_VALUES = ["policy", "procedura", "manuale", "contratto", "registro", "altro"] as const;

const NORMATIVE_ROLE_KEYS = [
  "ciso", "compliance_officer", "risk_manager", "internal_auditor", "external_auditor",
  "plant_manager", "control_owner", "plant_security_officer", "nis2_contact", "dpo",
  "isms_manager", "comitato_membro", "bu_referente", "raci_responsible", "raci_accountable",
] as const;

type EditingPolicy = Partial<DocumentWorkflowPolicy> & { id?: string };

function RoleMultiSelect({
  value,
  onChange,
}: {
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const { t } = useTranslation();

  function toggle(role: string) {
    onChange(value.includes(role) ? value.filter((r) => r !== role) : [...value, role]);
  }

  return (
    <div className="grid grid-cols-2 gap-1 max-h-40 overflow-y-auto border rounded px-2 py-1 bg-gray-50">
      {NORMATIVE_ROLE_KEYS.map((roleKey) => (
        <label key={roleKey} className="flex items-center gap-1 text-xs text-gray-700">
          <input
            type="checkbox"
            checked={value.includes(roleKey)}
            onChange={() => toggle(roleKey)}
            className="rounded"
          />
          <span>{t(`governance.roles.${roleKey}`)}</span>
        </label>
      ))}
    </div>
  );
}

export function DocumentWorkflowPage() {
  return <DocumentWorkflowSection embedded={false} />;
}

export function DocumentWorkflowSection({ embedded }: { embedded?: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<EditingPolicy | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<DocumentWorkflowPolicy | null>(null);

  const { data: policies = [], isLoading } = useQuery({
    queryKey: ["governance-document-workflow"],
    queryFn: governanceApi.listDocumentPolicies,
    retry: false,
  });

  const { data: plants = [] } = useQuery({
    queryKey: ["plants"],
    queryFn: plantsApi.list,
    retry: false,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editing) return;
      const payload: Partial<DocumentWorkflowPolicy> = {
        document_type: editing.document_type!,
        scope_type: editing.scope_type || "org",
        scope_id: editing.scope_type === "org" ? null : editing.scope_id || null,
        submit_roles: editing.submit_roles ?? [],
        review_roles: editing.review_roles ?? [],
        approve_roles: editing.approve_roles ?? [],
      };
      if (editing.id) {
        await governanceApi.updateDocumentPolicy(editing.id, payload);
      } else {
        await governanceApi.createDocumentPolicy(payload);
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["governance-document-workflow"] });
      setEditing(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await governanceApi.deleteDocumentPolicy(id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["governance-document-workflow"] });
      setConfirmDelete(null);
    },
  });

  function openNew() {
    setEditing({
      document_type: "policy",
      scope_type: "org",
      submit_roles: [],
      review_roles: [],
      approve_roles: [],
    });
  }

  function editPolicy(p: DocumentWorkflowPolicy) {
    setEditing({
      ...p,
    });
  }

  function scopeLabel(p: DocumentWorkflowPolicy): string {
    if (p.scope_type === "org") return t("governance.workflow.scope_org");
    if (p.scope_type === "bu") return t("governance.workflow.scope_bu");
    if (p.scope_type === "plant") {
      const plant = plants.find((pl) => pl.id === p.scope_id);
      if (plant) return `${t("governance.workflow.scope_site_prefix")} ${plant.code} — ${plant.name}`;
      return t("governance.workflow.scope_site_id");
    }
    return p.scope_type;
  }

  return (
    <div className={embedded ? "space-y-5" : "p-6 max-w-5xl mx-auto space-y-5"}>
      {!embedded && (
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{t("governance.workflow.title")}</h2>
            <p className="text-sm text-gray-500 mt-1">
              {t("governance.workflow.subtitle")}
            </p>
          </div>
          <ModuleHelp
            title={t("governance.workflow.title")}
            description="Configura il flusso di approvazione documentale per tipo documento (policy, procedura, manuale...) e plant."
            steps={[
              "Scegli il tipo documento e lo scope (org / BU / plant)",
              "Assegna i ruoli che possono creare/inviare in revisione",
              "Assegna i ruoli che devono revisionare",
              "Assegna i ruoli che possono approvare e mandare in vigore",
            ]}
            connections={[
              { module: "M07 Documenti", relation: "Abilita i pulsanti Invia per revisione / Approva" },
              { module: "M00 Governance", relation: "Usa i ruoli normativi (CISO, Plant Manager, ISMS...)" },
            ]}
          />
        </div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">{t("governance.workflow.configured_policies")}</h3>
        <button
          type="button"
          onClick={openNew}
          className="px-3 py-1.5 rounded bg-primary-600 text-white text-xs font-medium hover:bg-primary-700"
        >
          {t("governance.workflow.new_policy")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200">
        {isLoading ? (
          <div className="p-6 text-sm text-gray-400">{t("common.loading")}</div>
        ) : !policies.length ? (
          <div className="p-6 text-sm text-gray-400 italic">
            {t("governance.workflow.no_policies")}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-600">{t("governance.workflow.doc_type_col")}</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">{t("governance.workflow.scope_label")}</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">{t("governance.workflow.who_can_submit")}</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">{t("governance.workflow.who_reviews")}</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">{t("governance.workflow.who_approves")}</th>
                <th className="px-4 py-2 text-right font-medium text-gray-600">{t("governance.workflow.actions_col")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {policies.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-2 text-gray-800">
                    {t(`governance.workflow.doc_types.${p.document_type}`, p.document_type)}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-700">{scopeLabel(p)}</td>
                  <td className="px-4 py-2 text-xs text-gray-700">
                    {p.submit_roles?.length
                      ? p.submit_roles.map((r) => t(`governance.roles.${r}`, r)).join(", ")
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-700">
                    {p.review_roles?.length
                      ? p.review_roles.map((r) => t(`governance.roles.${r}`, r)).join(", ")
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-700">
                    {p.approve_roles?.length
                      ? p.approve_roles.map((r) => t(`governance.roles.${r}`, r)).join(", ")
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => editPolicy(p)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-0.5 mr-2"
                    >
                      {t("actions.edit")}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(p)}
                      className="text-xs text-red-600 hover:text-red-800 border border-red-200 rounded px-2 py-0.5"
                    >
                      {t("actions.delete")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal create/edit */}
      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {editing.id ? t("governance.workflow.modal_edit") : t("governance.workflow.modal_new")}
              </h3>
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="text-gray-400 hover:text-gray-700 text-xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.workflow.doc_type_col")}</label>
                <select
                  value={editing.document_type || "policy"}
                  onChange={(e) => setEditing((prev) => ({ ...prev!, document_type: e.target.value }))}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  {DOCUMENT_TYPE_VALUES.map((v) => (
                    <option key={v} value={v}>{t(`governance.workflow.doc_types.${v}`, v)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.workflow.scope_label")}</label>
                <select
                  value={editing.scope_type || "org"}
                  onChange={(e) =>
                    setEditing((prev) => ({
                      ...prev!,
                      scope_type: e.target.value as DocumentWorkflowPolicy["scope_type"],
                      scope_id: null,
                    }))
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="org">{t("governance.workflow.scope_org_option")}</option>
                  <option value="plant">{t("governance.workflow.scope_site_option")}</option>
                  {/* BU supportata lato backend, ma UI minimal per ora */}
                </select>
              </div>
              {editing.scope_type === "plant" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.workflow.site_label")}</label>
                  <select
                    value={editing.scope_id || ""}
                    onChange={(e) => setEditing((prev) => ({ ...prev!, scope_id: e.target.value || null }))}
                    className="w-full border rounded px-3 py-2 text-sm"
                  >
                    <option value="">{t("governance.workflow.site_select")}</option>
                    {plants.map((p) => (
                      <option key={p.id} value={p.id}>
                        [{p.code}] {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1">
                  {t("governance.workflow.who_can_create_submit")}
                </p>
                <RoleMultiSelect
                  value={editing.submit_roles || []}
                  onChange={(next) => setEditing((prev) => ({ ...prev!, submit_roles: next }))}
                />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1">{t("governance.workflow.who_reviews")}</p>
                <RoleMultiSelect
                  value={editing.review_roles || []}
                  onChange={(next) => setEditing((prev) => ({ ...prev!, review_roles: next }))}
                />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1">{t("governance.workflow.who_approves")}</p>
                <RoleMultiSelect
                  value={editing.approve_roles || []}
                  onChange={(next) => setEditing((prev) => ({ ...prev!, approve_roles: next }))}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("actions.cancel")}
              </button>
              <button
                type="button"
                onClick={() => saveMutation.mutate()}
                disabled={
                  saveMutation.isPending ||
                  !editing.document_type ||
                  !editing.scope_type ||
                  (editing.scope_type === "plant" && !editing.scope_id)
                }
                className="px-4 py-2 rounded text-sm bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? t("governance.workflow.saving") : t("governance.workflow.save_policy")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal delete */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">{t("governance.workflow.delete_title")}</h3>
            <p className="text-sm text-gray-600">
              {t("governance.workflow.delete_confirm")}{" "}
              <strong>
                {t(`governance.workflow.doc_types.${confirmDelete.document_type}`, confirmDelete.document_type)}
              </strong>{" "}
              ({scopeLabel(confirmDelete)})?
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("actions.cancel")}
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(confirmDelete.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded text-sm bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? t("governance.workflow.deleting") : t("actions.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
