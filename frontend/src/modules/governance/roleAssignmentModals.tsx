/** Nomina, termine e sostituzione delle responsabilità di governance
 *  (RoleAssignment): usate da Governance e dalla scheda utente, così il
 *  flusso (storico, motivo, passaggio di consegne) è uno solo. */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { governanceApi, type RoleAssignment } from "../../api/endpoints/governance";
import { plantsApi } from "../../api/endpoints/plants";
import { fetchAllPages } from "../../api/pagination";
import { todayISO } from "../../utils/dates";

export const ROLE_KEYS: Record<string, string> = {
  ciso:                   "ciso",
  compliance_officer:     "compliance_officer",
  risk_manager:           "risk_manager",
  internal_auditor:       "internal_auditor",
  external_auditor:       "external_auditor",
  plant_manager:          "plant_manager",
  control_owner:          "control_owner",
  plant_security_officer: "plant_security_officer",
  nis2_contact:           "nis2_contact",
  dpo:                    "dpo",
  isms_manager:           "isms_manager",
  comitato_membro:        "comitato_membro",
  bu_referente:           "bu_referente",
  raci_responsible:       "raci_responsible",
  raci_accountable:       "raci_accountable",
};

const TODAY = todayISO();

// ── Modal: Nuova assegnazione ─────────────────────────────────────────────────

export function RoleAssignmentModal({
  users,
  onClose,
  initial,
  lockUser = false,
}: {
  users: { id: number; email: string; name: string }[];
  onClose: () => void;
  initial?: Partial<Record<string, any>>;
  /** utente prefissato in `initial.user` e non modificabile */
  lockUser?: boolean;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, any>>({
    scope_type: "org",
    valid_from: TODAY,
    ...initial,
  });
  const [error, setError] = useState("");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const { data: busData } = useQuery({
    queryKey: ["business-units"],
    queryFn: () => fetchAllPages("/plants/business-units/"),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => governanceApi.createRoleAssignment(form as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-coverage-matrix"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (e: any) => {
      // Errori di validazione per campo ({"role": ["..."]}): mostra il messaggio,
      // non il JSON grezzo (es. ruolo già assegnato a un titolare attivo).
      const data = e?.response?.data;
      const fieldMessage = data && typeof data === "object"
        ? Object.values(data).flat().find((v): v is string => typeof v === "string")
        : undefined;
      setError(data?.detail || fieldMessage || t("common.error"));
    },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const val = e.target.value || null;
    if (e.target.name === "scope_type") {
      setForm(prev => ({ ...prev, scope_type: val, scope_id: null }));
    } else {
      setForm(prev => ({ ...prev, [e.target.name]: val }));
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("governance.roles_assign.modal_title")}</h3>
        <div className="space-y-3">
          {/* utente già scelto (es. dalla scheda utente): non si cambia qui */}
          {lockUser ? (
            <p className="text-sm text-gray-700">
              {t("governance.roles_assign.user")}: <strong>{users.find(u => u.id === form.user)?.name || users.find(u => u.id === form.user)?.email}</strong>
            </p>
          ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.user")} *</label>
            <select name="user" value={form.user ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {users.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
            </select>
          </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.role")} *</label>
            <select name="role" value={form.role ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {Object.keys(ROLE_KEYS).map((k) => (
                <option key={k} value={k}>{t(`governance.roles.${ROLE_KEYS[k]}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.scope")}</label>
            <select name="scope_type" value={form.scope_type ?? "org"} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="org">{t("governance.scopes.org")}</option>
              <option value="bu">{t("governance.scopes.bu")}</option>
              <option value="plant">{t("governance.scopes.plant")}</option>
            </select>
          </div>
          {form.scope_type === "bu" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.business_unit")} *</label>
              <select name="scope_id" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("governance.roles_assign.select_bu")}</option>
                {(busData ?? []).map((b: any) => (
                  <option key={b.id} value={b.id}>{b.code} — {b.name}</option>
                ))}
              </select>
            </div>
          )}
          {form.scope_type === "plant" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.plant")} *</label>
              <select name="scope_id" value={form.scope_id ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("governance.roles_assign.select_plant")}</option>
                {(plants ?? []).map((p) => (
                  <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.valid_from")} *</label>
              <input type="date" name="valid_from" defaultValue={TODAY} onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.valid_until")}</label>
              <input type="date" name="valid_until" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={
              mutation.isPending || !form.user || !form.role || !form.valid_from ||
              (form.scope_type !== "org" && !form.scope_id)
            }
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("governance.roles_assign.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Termina ruolo ──────────────────────────────────────────────────────

export function TerminaModal({
  assignment,
  onClose,
  onSuccess,
}: { assignment: RoleAssignment; onClose: () => void; onSuccess: (msg: string) => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(TODAY);
  const [error, setError] = useState("");

  function roleLabel(role: string) {
    const key = ROLE_KEYS[role] ?? role;
    return t(`governance.roles.${key}`, { defaultValue: role });
  }

  const mutation = useMutation({
    mutationFn: () => governanceApi.terminaRole(assignment.id, { reason, termination_date: date }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-coverage-matrix"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      qc.invalidateQueries({ queryKey: ["users"] });
      onSuccess(data.message);
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || t("governance.terminate.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-semibold">{t("governance.terminate.title")}</h3>
        <p className="text-sm text-gray-600">
          {t("governance.terminate.body", {
            role: roleLabel(assignment.role),
            user: assignment.user_name ?? assignment.user_email,
          })}
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.terminate.end_date")}</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.terminate.reason")} *</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={3}
            placeholder={t("governance.terminate.reason_placeholder")}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || reason.trim().length < 5}
            className="px-4 py-2 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("governance.terminate.pending") : t("governance.terminate.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Sostituisci ruolo ──────────────────────────────────────────────────

export function SostituisciModal({
  assignment,
  users,
  onClose,
  onSuccess,
}: {
  assignment: RoleAssignment;
  users: { id: number; email: string; name: string }[];
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [newUserId, setNewUserId] = useState<number | "">("");
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(TODAY);
  const [error, setError] = useState("");

  function roleLabel(role: string) {
    const key = ROLE_KEYS[role] ?? role;
    return t(`governance.roles.${key}`, { defaultValue: role });
  }

  const mutation = useMutation({
    mutationFn: () =>
      governanceApi.sostituisciRole(assignment.id, {
        new_user_id: newUserId as number,
        reason,
        handover_date: date,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-coverage-matrix"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      qc.invalidateQueries({ queryKey: ["users"] });
      onSuccess(data.message);
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || t("governance.replace.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-semibold">{t("governance.replace.title")}</h3>
        <p className="text-sm text-gray-600">
          {t("governance.replace.body", {
            role: roleLabel(assignment.role),
            user: assignment.user_name ?? assignment.user_email,
          })}
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.replace.new_owner")} *</label>
          <select
            value={newUserId}
            onChange={e => setNewUserId(Number(e.target.value))}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">{t("common.select")}</option>
            {users.filter(u => u.id !== assignment.user).map(u => (
              <option key={u.id} value={u.id}>{u.name || u.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.replace.handover_date")}</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.replace.reason")}</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
            placeholder={t("common.optional")}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !newUserId}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("governance.replace.pending") : t("governance.replace.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

