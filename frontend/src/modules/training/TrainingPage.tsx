import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { trainingApi, type TrainingCourse } from "../../api/endpoints/training";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useTranslation } from "react-i18next";

const sourceBadge: Record<string, string> = {
  interno: "bg-blue-100 text-blue-800",
  kb4: "bg-purple-100 text-purple-800",
  esterno: "bg-gray-100 text-gray-600",
};

function SourceBadge({ source }: { source: string }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${sourceBadge[source] ?? "bg-gray-100 text-gray-600"}`}>
      {t(`training.sources.${source}`, { defaultValue: source })}
    </span>
  );
}

function NewCourseModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<TrainingCourse>>({ source: "interno", status: "attivo", mandatory: false });

  const mutation = useMutation({
    mutationFn: trainingApi.createCourse,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["training-courses"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      setForm(prev => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else if (name === "duration_minutes") {
      setForm(prev => ({ ...prev, [name]: value ? Number(value) : null }));
    } else {
      setForm(prev => ({ ...prev, [name]: value }));
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">{t("training.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("training.fields.title")} *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("training.fields.description")}</label>
            <textarea name="description" onChange={handleChange} rows={2} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("training.fields.source")}</label>
              <select name="source" defaultValue="interno" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {(["interno", "kb4", "esterno"] as const).map(s => (
                  <option key={s} value={s}>{t(`training.sources.${s}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("training.fields.duration_minutes")}</label>
              <input name="duration_minutes" type="number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("training.fields.deadline")}</label>
              <input name="deadline" type="date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div className="flex items-center gap-2 mt-6">
              <input name="mandatory" id="mandatory" type="checkbox" onChange={handleChange} className="rounded border-gray-300" />
              <label htmlFor="mandatory" className="text-sm font-medium text-gray-700">{t("training.fields.mandatory")}</label>
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">{t("common.save_error")}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("training.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function TrainingPage() {
  const { t, i18n } = useTranslation();
  const [showNew, setShowNew] = useState(false);

  const { data: courses = [], isLoading } = useQuery({
    queryKey: ["training-courses"],
    queryFn: trainingApi.courses,
    retry: false,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("training.title")}</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          {t("training.new.open")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : courses.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("training.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("training.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("training.table.source")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("training.table.mandatory")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("training.table.duration")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("training.table.deadline")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("training.table.status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {courses.map(course => (
                <tr key={course.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{course.title}</td>
                  <td className="px-4 py-3"><SourceBadge source={course.source} /></td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${course.mandatory ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"}`}>
                      {course.mandatory ? t("common.yes") : t("common.no")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{course.duration_minutes ?? t("common.none")}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{course.deadline ? new Date(course.deadline).toLocaleDateString(i18n.language) : t("common.none")}</td>
                  <td className="px-4 py-3"><StatusBadge status={course.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewCourseModal onClose={() => setShowNew(false)} />}
    </div>
  );
}
