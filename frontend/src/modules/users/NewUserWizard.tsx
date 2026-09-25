import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { usersApi } from "../../api/endpoints/users";
import { plantsApi } from "../../api/endpoints/plants";
import {
  ROLE_ICON, RoleCards, RolePermissionsPreview, ScopePicker, emptyScope, roleName, scopeReady, scopeToAccess,
  type ScopeValue,
} from "./shared";

type Step = 0 | 1 | 2 | 3;

/** Nuovo utente in quattro passi: chi è → cosa fa → dove → riepilogo. */
export function NewUserWizard({ onClose, onCreated }: { onClose: () => void; onCreated: (id: number) => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>(0);
  const [who, setWho] = useState({ username: "", email: "", first_name: "", last_name: "", password: "" });
  const [role, setRole] = useState("");
  const [scope, setScope] = useState<ScopeValue>(emptyScope);
  const [error, setError] = useState("");
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list() });
  const { data: bus = [] } = useQuery({ queryKey: ["business-units"], queryFn: () => plantsApi.businessUnits() });

  const create = useMutation({
    mutationFn: () => usersApi.create({ ...who, accesses: role ? [{ role, ...scopeToAccess(scope) }] : [] }),
    onSuccess: u => { qc.invalidateQueries({ queryKey: ["users"] }); onCreated(u.id); },
    onError: e => {
      const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
      setError(data ? Object.values(data).flat().map(v => (typeof v === "object" ? Object.values(v as object).flat().join(" ") : String(v))).join(" ") : t("common.save_error"));
    },
  });

  const whoOk = who.username.trim() && who.email.includes("@") && who.password.length >= 12;
  const canNext = step === 0 ? !!whoOk : step === 1 ? true : step === 2 ? (!role || scopeReady(scope)) : true;
  const steps = ["who", "role", "where", "summary"] as const;
  const scopeText = scope.kind === "org" ? t("users.scope.org")
    : scope.kind === "bu" ? t("users.scope.bu_named", { code: bus.find(b => b.id === scope.bu)?.code ?? "—" })
      : plants.filter(p => scope.sites.includes(p.id)).map(p => p.code).join(", ");

  const input = (name: keyof typeof who, label: string, type = "text", hint?: string) => (
    <label className="block">
      <span className="block text-xs font-medium text-gray-600 mb-1">{label}</span>
      <input type={type} value={who[name]} onChange={e => setWho(p => ({ ...p, [name]: e.target.value }))}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" aria-label={label} />
      {hint && <span className="block text-[11px] text-gray-400 mt-0.5">{hint}</span>}
    </label>
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="px-6 pt-5 pb-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">{t("users.wizard.title")}</h3>
            <button onClick={onClose} aria-label={t("users.drawer.close")} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">×</button>
          </div>
          <ol className="flex items-center gap-2 mt-3">
            {steps.map((s, i) => (
              <li key={s} className="flex items-center gap-2 text-xs">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center font-medium ${i < step ? "bg-primary-600 text-white" : i === step ? "bg-primary-100 text-primary-800 ring-2 ring-primary-300" : "bg-gray-100 text-gray-400"}`}>
                  {i < step ? "✓" : i + 1}
                </span>
                <span className={i === step ? "text-gray-900 font-medium" : "text-gray-400"}>{t(`users.wizard.step_${s}`)}</span>
                {i < steps.length - 1 && <span className="w-6 h-px bg-gray-200" />}
              </li>
            ))}
          </ol>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {step === 0 && (
            <div className="grid grid-cols-2 gap-3">
              {input("first_name", t("users.fields.first_name"))}
              {input("last_name", t("users.fields.last_name"))}
              {input("email", `${t("users.fields.email")} *`, "email")}
              {input("username", `${t("users.fields.username")} *`)}
              <div className="col-span-2">{input("password", `${t("users.fields.password")} *`, "password", t("users.fields.password_hint"))}</div>
            </div>
          )}
          {step === 1 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">{t("users.wizard.role_intro")}</p>
              <RoleCards value={role} onChange={setRole} />
              {role && <RolePermissionsPreview role={role} />}
            </div>
          )}
          {step === 2 && (
            role ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">{t("users.wizard.where_intro", { role: roleName(t, role) })}</p>
                <ScopePicker value={scope} onChange={setScope} />
              </div>
            ) : <p className="text-sm text-gray-500">{t("users.wizard.no_role")}</p>
          )}
          {step === 3 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-gray-200 p-4">
                <p className="text-base font-medium text-gray-900">{[who.first_name, who.last_name].filter(Boolean).join(" ") || who.username}</p>
                <p className="text-sm text-gray-500">{who.email} · {who.username}</p>
              </div>
              {role ? (
                <div className="rounded-xl border border-gray-200 p-4 space-y-3">
                  <p className="text-sm text-gray-800">
                    <span aria-hidden>{ROLE_ICON[role]}</span> <strong>{roleName(t, role)}</strong> · 📍 {scopeText}
                  </p>
                  <RolePermissionsPreview role={role} compact />
                </div>
              ) : (
                <p className="text-sm text-amber-800 bg-amber-50 rounded-lg px-3 py-2">{t("users.wizard.no_role")}</p>
              )}
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex justify-between">
          <button onClick={() => (step === 0 ? onClose() : setStep((step - 1) as Step))}
            className="px-4 py-2 text-sm border rounded-lg text-gray-600">{step === 0 ? t("actions.cancel") : t("users.wizard.back")}</button>
          {step < 3 ? (
            <button onClick={() => setStep((step + 1) as Step)} disabled={!canNext}
              className="px-4 py-2 text-sm rounded-lg bg-primary-600 text-white disabled:opacity-50">{t("users.wizard.next")}</button>
          ) : (
            <button onClick={() => create.mutate()} disabled={create.isPending}
              className="px-4 py-2 text-sm rounded-lg bg-primary-600 text-white disabled:opacity-50">{t("users.wizard.create")}</button>
          )}
        </div>
      </div>
    </div>
  );
}
