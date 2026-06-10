import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type Supplier, type SupplierQuestionnaire } from "../../api/endpoints/suppliers";
import { useTranslation } from "react-i18next";

export function SendQuestionnaireModal({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [templateId, setTemplateId] = useState("");
  const [error, setError] = useState("");

  const { data: templates } = useQuery({
    queryKey: ["questionnaire-templates"],
    queryFn: suppliersApi.listTemplates,
  });

  const mutation = useMutation({
    mutationFn: () => suppliersApi.sendQuestionnaire(supplier.id, templateId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || t("suppliers.send.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
        <h3 className="text-base font-semibold mb-1">{t("suppliers.send.title")}</h3>
        <p className="text-sm text-gray-500 mb-1">
          {t("suppliers.send.supplier_label")}: <strong>{supplier.name}</strong>
        </p>
        <div className="mb-3 text-sm space-y-0.5">
          <p>
            <span className="text-gray-500">{t("suppliers.send.to_label")}:</span>{" "}
            {supplier.email || <span className="text-red-500">{t("suppliers.send.email_missing")}</span>}
          </p>
          {(supplier.additional_emails?.length ?? 0) > 0 && (
            <p>
              <span className="text-gray-500">{t("suppliers.send.cc_label")}:</span>{" "}
              <span className="text-gray-700">
                {supplier.additional_emails.join(", ")}
              </span>
            </p>
          )}
        </div>
        {!supplier.email && (
          <p className="text-sm text-red-600 bg-red-50 rounded p-2 mb-3">{t("suppliers.send.email_warn")}</p>
        )}
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.send.template_label")}</label>
          <select value={templateId} onChange={e => setTemplateId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
            <option value="">{t("suppliers.send.template_select")}</option>
            {(templates ?? []).map(tpl => <option key={tpl.id} value={tpl.id}>{tpl.name}</option>)}
          </select>
        </div>
        {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600">{t("actions.cancel")}</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !templateId || !supplier.email} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
            {mutation.isPending ? t("suppliers.send.sending") : t("suppliers.send.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function EvaluateModal({ questionnaire, onClose }: { questionnaire: SupplierQuestionnaire; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [evalDate, setEvalDate] = useState("");
  const [riskResult, setRiskResult] = useState<string>("medio");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => suppliersApi.evaluateQuestionnaire(questionnaire.id, evalDate, riskResult, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || t("suppliers.evaluate.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
        <h3 className="text-base font-semibold mb-1">{t("suppliers.evaluate.title")}</h3>
        <p className="text-sm text-gray-500 mb-3">{t("suppliers.evaluate.supplier_label")}: <strong>{questionnaire.supplier_name}</strong></p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.evaluate.date_label")}</label>
            <input type="date" value={evalDate} onChange={e => setEvalDate(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.evaluate.result_label")}</label>
            <select value={riskResult} onChange={e => setRiskResult(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
              {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{t(`suppliers.risk.${r}`)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.evaluate.notes_label")}</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" rows={2} placeholder={t("suppliers.evaluate.notes_placeholder")} />
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600">{t("actions.cancel")}</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !evalDate} className="px-3 py-1.5 bg-green-600 text-white rounded text-sm disabled:opacity-50">
            {mutation.isPending ? t("suppliers.evaluate.saving") : t("suppliers.evaluate.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}
