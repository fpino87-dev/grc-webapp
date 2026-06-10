import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type QuestionnaireTemplate } from "../../api/endpoints/suppliers";
import { useTranslation } from "react-i18next";

// Default in italiano: è il contenuto dell'email inviata ai fornitori (dato,
// non UI) — l'utente lo personalizza per lingua/destinatario nel template.
const TEMPLATE_DEFAULT_SUBJECT = "Questionario di valutazione fornitore — {supplier_name}";
const TEMPLATE_DEFAULT_BODY =
  "Gentile {supplier_name},\n\n" +
  "nell'ambito del nostro processo di qualifica e monitoraggio fornitori, Le chiediamo di compilare il questionario di valutazione al seguente link:\n\n" +
  "{questionnaire_link}\n\n" +
  "Il questionario richiede circa 10-15 minuti. Le chiediamo di completarlo entro 7 giorni dal ricevimento di questa email.\n\n" +
  "Per qualsiasi chiarimento può rispondere a questa email.\n\n" +
  "Cordiali saluti,\n" +
  "Team Compliance";

function TemplateModal({ template, onClose }: { template?: QuestionnaireTemplate; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const isEdit = !!template;
  const [form, setForm] = useState<Partial<QuestionnaireTemplate>>(
    template
      ? { ...template }
      : { name: "", subject: TEMPLATE_DEFAULT_SUBJECT, body: TEMPLATE_DEFAULT_BODY, form_url: "" }
  );
  const [error, setError] = useState("");

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  const mutation = useMutation({
    mutationFn: () => isEdit ? suppliersApi.updateTemplate(template!.id, form) : suppliersApi.createTemplate(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["questionnaire-templates"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || t("suppliers.templates.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6">
        <h3 className="text-lg font-semibold mb-4">{isEdit ? t("suppliers.templates.modal_edit_title") : t("suppliers.templates.modal_new_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.templates.name_label")}</label>
            <input name="name" value={form.name ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.templates.url_label")}</label>
            <input name="form_url" type="url" value={form.form_url ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="https://forms.example.com/..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.templates.subject_label")}</label>
            <input name="subject" value={form.subject ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("suppliers.templates.body_label")}</label>
            <p className="text-xs text-gray-400 mb-1">{t("suppliers.templates.body_vars_hint")}: <code className="bg-gray-100 px-1 rounded">{"{supplier_name}"}</code> + <code className="bg-gray-100 px-1 rounded">{"{questionnaire_link}"}</code></p>
            <textarea name="body" value={form.body ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm font-mono" rows={10} />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name || !form.form_url || !form.subject || !form.body} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? t("common.saving") : isEdit ? t("suppliers.templates.update_btn") : t("suppliers.templates.create_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function TemplateTab() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [modal, setModal] = useState<null | "new" | QuestionnaireTemplate>(null);

  const { data: templates, isLoading } = useQuery({
    queryKey: ["questionnaire-templates"],
    queryFn: suppliersApi.listTemplates,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.deleteTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["questionnaire-templates"] }),
  });

  return (
    <div>
      {modal === "new" && <TemplateModal onClose={() => setModal(null)} />}
      {modal && modal !== "new" && <TemplateModal template={modal as QuestionnaireTemplate} onClose={() => setModal(null)} />}

      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-gray-500">{t("suppliers.templates.hint")}</p>
        <button onClick={() => setModal("new")} className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700">
          {t("suppliers.templates.new_btn")}
        </button>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-400 py-8">{t("common.loading")}</div>
      ) : !templates?.length ? (
        <div className="text-center text-gray-400 py-8 border border-dashed rounded-lg">
          {t("suppliers.templates.none")}
        </div>
      ) : (
        <div className="grid gap-4">
          {templates.map(tpl => (
            <div key={tpl.id} className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-gray-800">{tpl.name}</h4>
                  <p className="text-xs text-gray-500 mt-0.5">{t("suppliers.templates.subject_prefix")}: {tpl.subject}</p>
                  <p className="text-xs text-indigo-600 mt-0.5 truncate">{t("suppliers.templates.form_prefix")}: {tpl.form_url}</p>
                  <pre className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-2 whitespace-pre-wrap max-h-32 overflow-hidden font-sans">{tpl.body}</pre>
                </div>
                <div className="flex gap-2 ml-3 shrink-0">
                  <button onClick={() => setModal(tpl)} className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-1 hover:bg-indigo-50">
                    {t("actions.edit")}
                  </button>
                  <button
                    onClick={() => { if (window.confirm(t("suppliers.templates.delete_confirm", { name: tpl.name }))) deleteMutation.mutate(tpl.id); }}
                    disabled={deleteMutation.isPending}
                    className="text-xs text-red-600 border border-red-200 rounded px-2 py-1 hover:bg-red-50 disabled:opacity-50"
                  >
                    {t("actions.delete")}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
