import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { CpvInput } from "./CpvInput";
import { useTranslation } from "react-i18next";

// ─── Editor email aggiuntive (CC) ────────────────────────────────────────────

function isValidEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s.trim());
}

export function EmailListEditor({
  value,
  onChange,
}: {
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const { t } = useTranslation();
  const list = value ?? [];
  return (
    <div className="space-y-1.5">
      {list.map((email, idx) => {
        const valid = !email || isValidEmail(email);
        return (
          <div key={idx} className="flex items-center gap-2">
            <input
              type="email"
              value={email}
              onChange={e => {
                const next = [...list];
                next[idx] = e.target.value;
                onChange(next);
              }}
              placeholder="email@dominio.it"
              className={`flex-1 border rounded px-3 py-1.5 text-sm ${valid ? "" : "border-red-400 bg-red-50"}`}
            />
            <button
              type="button"
              onClick={() => onChange(list.filter((_, i) => i !== idx))}
              className="text-red-500 hover:text-red-700 px-2"
              title={t("suppliers.email_editor.remove_title")}
            >
              ×
            </button>
          </div>
        );
      })}
      <button
        type="button"
        onClick={() => onChange([...list, ""])}
        className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-1 hover:bg-indigo-50"
      >
        {t("suppliers.email_editor.add_btn")}
      </button>
    </div>
  );
}

// ─── Modal nuovo fornitore ───────────────────────────────────────────────────

export function NewSupplierModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({
    risk_level: "basso",
    status: "attivo",
    nis2_relevant: false,
    cpv_codes: [],
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); onClose(); },
    onError: (e: any) => {
      const data = e?.response?.data;
      if (data?.vat_number) setError(data.vat_number[0]);
      else if (data?.nis2_relevance_criterion) setError(data.nis2_relevance_criterion[0]);
      else if (data?.non_field_errors) setError(data.non_field_errors[0]);
      else setError(t("suppliers.form.save_error"));
    },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      setForm(prev => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else {
      setForm(prev => ({ ...prev, [name]: value }));
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto py-6">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-xl mx-4 p-6">
        <h3 className="text-lg font-semibold mb-4">{t("suppliers.form.new_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.name_label")}</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.vat_label")}</label>
              <input name="vat_number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="es. 01234567890" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.country_label")}</label>
              <input name="country" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="IT" maxLength={2} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.email_label")}</label>
            <input name="email" type="email" required onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="contatto@fornitore.it" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("suppliers.form.cc_label")}
            </label>
            <EmailListEditor
              value={form.additional_emails ?? []}
              onChange={emails => setForm(prev => ({ ...prev, additional_emails: emails }))}
            />
            <p className="mt-1 text-xs text-gray-500">
              {t("suppliers.form.cc_hint")}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.description_label")}</label>
            <textarea name="description" rows={2} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("suppliers.form.description_placeholder")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.risk_label")}</label>
              <select name="risk_level" defaultValue="basso" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{t(`suppliers.risk.${r}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.eval_date_label")}</label>
              <input name="evaluation_date" type="date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>

          {/* Sezione ACN / NIS2 */}
          <div className="border-t border-gray-200 pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("suppliers.form.acn_section")}</p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t("suppliers.form.cpv_label")}</label>
              <CpvInput
                value={form.cpv_codes ?? []}
                onChange={codes => setForm(prev => ({ ...prev, cpv_codes: codes }))}
                description={form.description ?? ""}
              />
            </div>
            <div className="flex items-center gap-2 mt-3">
              <input
                type="checkbox"
                name="nis2_relevant"
                id="new_nis2_relevant"
                checked={!!form.nis2_relevant}
                onChange={handleChange}
                className="h-4 w-4 text-purple-600 border-gray-300 rounded"
              />
              <label htmlFor="new_nis2_relevant" className="text-sm font-medium text-gray-700">
                {t("suppliers.form.nis2_relevant_label")}
              </label>
            </div>
            {form.nis2_relevant && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.criterion_label")}</label>
                  <select name="nis2_relevance_criterion" value={form.nis2_relevance_criterion ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                    <option value="">{t("suppliers.form.criterion_select")}</option>
                    <option value="ict">{t("suppliers.form.criterion_ict")}</option>
                    <option value="non_fungibile">{t("suppliers.form.criterion_nf")}</option>
                    <option value="entrambi">{t("suppliers.form.criterion_both")}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.concentration_label")}</label>
                  <div className="relative">
                    <input
                      name="supply_concentration_pct"
                      type="number"
                      min={0}
                      max={100}
                      step={0.01}
                      onChange={handleChange}
                      className="w-full border rounded px-3 py-2 text-sm pr-8"
                      placeholder="es. 35.00"
                    />
                    <span className="absolute right-2 top-2 text-gray-400 text-sm">%</span>
                  </div>
                  {form.supply_concentration_pct !== undefined && form.supply_concentration_pct !== null && String(form.supply_concentration_pct) !== "" && (
                    <p className="text-xs mt-0.5 text-gray-500">
                      {t("suppliers.concentration.threshold_prefix")}: {Number(form.supply_concentration_pct) < 20 ? t("suppliers.concentration.bassa") : Number(form.supply_concentration_pct) <= 50 ? t("suppliers.concentration.media") : t("suppliers.concentration.critica")}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => { setError(""); mutation.mutate(form); }}
            disabled={mutation.isPending || !form.name || !form.email}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("suppliers.form.create_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal modifica fornitore ────────────────────────────────────────────────

export function EditSupplierModal({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({ ...supplier, cpv_codes: supplier.cpv_codes ?? [] });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => suppliersApi.update(supplier.id, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); onClose(); },
    onError: (e: any) => {
      const data = e?.response?.data;
      if (data?.vat_number) setError(data.vat_number[0]);
      else if (data?.nis2_relevance_criterion) setError(data.nis2_relevance_criterion[0]);
      else if (data?.non_field_errors) setError(data.non_field_errors[0]);
      else setError(t("suppliers.form.save_error"));
    },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      setForm(prev => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else {
      setForm(prev => ({ ...prev, [name]: value }));
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto py-6">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-xl mx-4 p-6">
        <h3 className="text-lg font-semibold mb-4">{t("suppliers.form.edit_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.name_label")}</label>
            <input name="name" value={form.name ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.vat_label")}</label>
              <input name="vat_number" value={form.vat_number ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.country_label")}</label>
              <input name="country" value={form.country ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="IT" maxLength={2} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.email_label")}</label>
            <input name="email" type="email" required value={form.email ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="contatto@fornitore.it" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("suppliers.form.cc_label")}
            </label>
            <EmailListEditor
              value={form.additional_emails ?? []}
              onChange={emails => setForm(prev => ({ ...prev, additional_emails: emails }))}
            />
            <p className="mt-1 text-xs text-gray-500">
              {t("suppliers.form.cc_hint")}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.description_label")}</label>
            <textarea name="description" rows={2} value={form.description ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("suppliers.form.description_placeholder")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.risk_label")}</label>
              <select name="risk_level" value={form.risk_level ?? "basso"} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{t(`suppliers.risk.${r}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.status_label")}</label>
              <select name="status" value={form.status ?? "attivo"} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["attivo","sospeso","terminato"].map(s => <option key={s} value={s}>{t(`suppliers.list.status_${s}`)}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.eval_date_label")}</label>
            <input name="evaluation_date" type="date" value={form.evaluation_date ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          {/* Sezione ACN / NIS2 */}
          <div className="border-t border-gray-200 pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("suppliers.form.acn_section")}</p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t("suppliers.form.cpv_label")}</label>
              <CpvInput
                value={form.cpv_codes ?? []}
                onChange={codes => setForm(prev => ({ ...prev, cpv_codes: codes }))}
                description={form.description ?? ""}
              />
            </div>
            <div className="flex items-center gap-2 mt-3">
              <input
                type="checkbox"
                name="nis2_relevant"
                id="edit_nis2_relevant"
                checked={!!form.nis2_relevant}
                onChange={handleChange}
                className="h-4 w-4 text-purple-600 border-gray-300 rounded"
              />
              <label htmlFor="edit_nis2_relevant" className="text-sm font-medium text-gray-700">
                {t("suppliers.form.nis2_relevant_label")}
              </label>
            </div>
            {form.nis2_relevant && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.criterion_label")}</label>
                  <select name="nis2_relevance_criterion" value={form.nis2_relevance_criterion ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                    <option value="">{t("suppliers.form.criterion_select")}</option>
                    <option value="ict">{t("suppliers.form.criterion_ict")}</option>
                    <option value="non_fungibile">{t("suppliers.form.criterion_nf")}</option>
                    <option value="entrambi">{t("suppliers.form.criterion_both")}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.concentration_label")}</label>
                  <div className="relative">
                    <input
                      name="supply_concentration_pct"
                      type="number"
                      min={0}
                      max={100}
                      step={0.01}
                      value={form.supply_concentration_pct ?? ""}
                      onChange={handleChange}
                      className="w-full border rounded px-3 py-2 text-sm pr-8"
                      placeholder="es. 35.00"
                    />
                    <span className="absolute right-2 top-2 text-gray-400 text-sm">%</span>
                  </div>
                  {form.supply_concentration_pct !== null && form.supply_concentration_pct !== undefined && String(form.supply_concentration_pct) !== "" && (
                    <p className="text-xs mt-0.5 text-gray-500">
                      {t("suppliers.concentration.threshold_prefix")}: {Number(form.supply_concentration_pct) < 20 ? t("suppliers.concentration.bassa") : Number(form.supply_concentration_pct) <= 50 ? t("suppliers.concentration.media") : t("suppliers.concentration.critica")}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => { setError(""); mutation.mutate(); }}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("suppliers.form.update_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}
