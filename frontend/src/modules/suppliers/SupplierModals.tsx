import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type Supplier, type SupplierDuplicates } from "../../api/endpoints/suppliers";
import { CpvInput } from "./CpvInput";
import { RegisterExistingEvaluationModal } from "./QuestionnaireModals";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

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

// ─── Rilevamento duplicati ───────────────────────────────────────────────────

/**
 * Controlla i possibili duplicati (P.IVA identica / ragione sociale simile)
 * mentre l'utente compila il form, con debounce. `checking` resta true finché
 * il controllo sui valori correnti non è concluso: il salvataggio attende.
 */
function useSupplierDuplicates(form: Partial<Supplier>, excludeId?: string) {
  const current = JSON.stringify({
    name: (form.name ?? "").trim(),
    vat_number: (form.vat_number ?? "").trim(),
    country: (form.country ?? "").trim() || "IT",
  });
  const [debounced, setDebounced] = useState(current);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(current), 400);
    return () => clearTimeout(timer);
  }, [current]);

  const params = JSON.parse(debounced) as { name: string; vat_number: string; country: string };
  const enabled = params.name.length >= 3 || params.vat_number.length > 0;
  const query = useQuery({
    queryKey: ["supplier-duplicates", debounced, excludeId],
    queryFn: () => suppliersApi.checkDuplicates({ ...params, exclude_id: excludeId }),
    enabled,
    staleTime: 30_000,
  });
  return {
    data: enabled ? query.data : undefined,
    checking: current !== debounced || (enabled && query.isFetching),
  };
}

function DuplicateWarning({
  data,
  confirmed,
  onConfirm,
  onOpenExisting,
}: {
  data: SupplierDuplicates | undefined;
  confirmed?: boolean;
  onConfirm?: (v: boolean) => void;
  onOpenExisting?: (id: string) => void;
}) {
  const { t } = useTranslation();
  if (!data) return null;
  const { vat_match, name_matches, hidden_name_matches } = data;
  const hasNameWarning = name_matches.length > 0 || hidden_name_matches > 0;
  if (!vat_match && !hasNameWarning) return null;

  const openBtn = (id: string) =>
    onOpenExisting && (
      <button type="button" onClick={() => onOpenExisting(id)} className="ml-2 text-xs text-indigo-700 underline hover:text-indigo-900">
        {t("suppliers.duplicates.open")}
      </button>
    );

  return (
    <div className="space-y-2">
      {vat_match && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {vat_match.visible ? (
            <>
              <span className="font-medium">{t("suppliers.duplicates.vat_exists")}</span>{" "}
              {vat_match.name} ({vat_match.vat_number}) — {t(`suppliers.list.status_${vat_match.status}`)}
              {openBtn(vat_match.id)}
            </>
          ) : (
            t("suppliers.duplicates.vat_exists_hidden")
          )}
        </div>
      )}
      {!vat_match && hasNameWarning && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <p className="font-medium">{t("suppliers.duplicates.similar_title")}</p>
          {name_matches.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {name_matches.map(m => (
                <li key={m.id}>
                  {m.name} ({m.vat_number || "—"}) — {t(`suppliers.list.status_${m.status}`)}
                  {openBtn(m.id)}
                </li>
              ))}
            </ul>
          )}
          {hidden_name_matches > 0 && (
            <p className="mt-1 text-xs">{t("suppliers.duplicates.similar_hidden", { count: hidden_name_matches })}</p>
          )}
          {onConfirm && (
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!confirmed} onChange={e => onConfirm(e.target.checked)} className="h-4 w-4" />
              {t("suppliers.duplicates.confirm_different")}
            </label>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Modal nuovo fornitore ───────────────────────────────────────────────────

export function NewSupplierModal({
  onClose,
  onOpenExisting,
}: {
  onClose: () => void;
  onOpenExisting?: (id: string) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({
    risk_level: "basso",
    status: "attivo",
    nis2_relevant: false,
    tisax_relevant: false,
    cpv_codes: [],
  });
  const [error, setError] = useState("");
  const dup = useSupplierDuplicates(form);
  const [similarConfirmed, setSimilarConfirmed] = useState(false);
  const dupSignature = dup.data ? dup.data.name_matches.map(m => m.id).join(",") + `|${dup.data.hidden_name_matches}` : "";
  // Nuovi nomi simili → la conferma "fornitore diverso" va ridata.
  useEffect(() => setSimilarConfirmed(false), [dupSignature]);
  const vatBlocked = !!dup.data?.vat_match;
  const needsConfirm = !!dup.data && !vatBlocked && (dup.data.name_matches.length > 0 || dup.data.hidden_name_matches > 0);

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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.form.risk_label")}</label>
            <select name="risk_level" defaultValue="basso" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{t(`suppliers.risk.${r}`)}</option>)}
            </select>
            <p className="mt-1 text-xs text-gray-500">{t("suppliers.form.eval_new_hint")}</p>
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

          {/* Sezione TISAX */}
          <div className="border-t border-gray-200 pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">TISAX</p>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                name="tisax_relevant"
                id="new_tisax_relevant"
                checked={!!form.tisax_relevant}
                onChange={handleChange}
                className="h-4 w-4 text-sky-600 border-gray-300 rounded"
              />
              <label htmlFor="new_tisax_relevant" className="text-sm font-medium text-gray-700">
                {t("suppliers.form.tisax_relevant_label")}
              </label>
            </div>
            <p className="mt-1 text-xs text-gray-500">{t("suppliers.form.tisax_relevant_hint")}</p>
          </div>
        </div>
        <div className="mt-3">
          <DuplicateWarning
            data={dup.data}
            confirmed={similarConfirmed}
            onConfirm={setSimilarConfirmed}
            onOpenExisting={onOpenExisting}
          />
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => { setError(""); mutation.mutate(form); }}
            disabled={
              mutation.isPending || !form.name || !form.email
              || dup.checking || vatBlocked || (needsConfirm && !similarConfirmed)
            }
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("suppliers.form.create_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Valutazione corrente (read-only) ────────────────────────────────────────

/**
 * Data/scadenza/origine dell'ultima valutazione: derivate dal backend
 * (questionario valutato, valutazione esistente registrata, audit approvato),
 * non modificabili a mano. Rilegge il fornitore dopo una registrazione.
 */
function EvaluationSummary({
  supplierId,
  initial,
  onRefreshed,
}: {
  supplierId: string;
  initial: Supplier;
  onRefreshed?: (fresh: Supplier) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [registerOpen, setRegisterOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["supplier", supplierId],
    queryFn: () => suppliersApi.get(supplierId),
    initialData: initial,
    staleTime: 0,
  });
  const s = data ?? initial;
  const fmt = (d: string) => new Date(d).toLocaleDateString(i18n.language || "it");
  const expired = !!s.evaluation_expires_at && new Date(s.evaluation_expires_at).getTime() < Date.now();

  return (
    <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm">
          <p className="font-medium text-gray-700">{t("suppliers.form.eval_summary_label")}</p>
          {s.evaluation_date ? (
            <p className="text-gray-700">
              {t("suppliers.form.eval_summary_date", { date: fmt(s.evaluation_date) })}
              {s.evaluation_source && (
                <span className="text-gray-500"> · {t(`suppliers.eval_source.${s.evaluation_source}`)}</span>
              )}
              {s.evaluation_expires_at && (
                <span className={expired ? "text-red-600 font-medium" : "text-gray-500"}>
                  {" · "}
                  {expired
                    ? t("suppliers.form.eval_summary_expired", { date: fmt(s.evaluation_expires_at) })
                    : t("suppliers.form.eval_summary_expires", { date: fmt(s.evaluation_expires_at) })}
                </span>
              )}
            </p>
          ) : (
            <p className="text-gray-500">{t("suppliers.form.eval_summary_none")}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setRegisterOpen(true)}
          className="shrink-0 text-xs text-green-700 border border-green-200 rounded px-2 py-1 hover:bg-green-50"
        >
          {t("suppliers.register_existing.btn")}
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-500">{t("suppliers.form.eval_summary_hint")}</p>
      {registerOpen && (
        <RegisterExistingEvaluationModal
          supplier={s}
          onClose={() => setRegisterOpen(false)}
          onSaved={async () => {
            // La registrazione può aggiornare anche il livello di rischio:
            // riallinea il form, altrimenti il salvataggio lo sovrascriverebbe.
            const fresh = await suppliersApi.get(supplierId);
            qc.setQueryData(["supplier", supplierId], fresh);
            onRefreshed?.(fresh);
          }}
        />
      )}
    </div>
  );
}

// ─── Modal modifica fornitore ────────────────────────────────────────────────

export function EditSupplierModal({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({ ...supplier, cpv_codes: supplier.cpv_codes ?? [] });
  const [error, setError] = useState("");
  // In modifica: P.IVA di un altro fornitore bloccante, nomi simili solo avviso.
  const dup = useSupplierDuplicates(form, supplier.id);

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
          <EvaluationSummary
            supplierId={supplier.id}
            initial={supplier}
            onRefreshed={fresh => setForm(prev => ({ ...prev, risk_level: fresh.risk_level }))}
          />

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

          {/* Sezione TISAX */}
          <div className="border-t border-gray-200 pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">TISAX</p>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                name="tisax_relevant"
                id="edit_tisax_relevant"
                checked={!!form.tisax_relevant}
                onChange={handleChange}
                className="h-4 w-4 text-sky-600 border-gray-300 rounded"
              />
              <label htmlFor="edit_tisax_relevant" className="text-sm font-medium text-gray-700">
                {t("suppliers.form.tisax_relevant_label")}
              </label>
            </div>
            <p className="mt-1 text-xs text-gray-500">{t("suppliers.form.tisax_relevant_hint")}</p>
          </div>
        </div>
        <div className="mt-3">
          <DuplicateWarning data={dup.data} />
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => { setError(""); mutation.mutate(); }}
            disabled={mutation.isPending || !form.name || !!dup.data?.vat_match}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("suppliers.form.update_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}
