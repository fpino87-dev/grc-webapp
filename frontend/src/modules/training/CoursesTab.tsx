import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  trainingApi,
  type AudienceKind,
  type ControlOption,
  type CourseKind,
  type TrainingCourse,
} from "../../api/endpoints/training";
import {
  Modal, apiErrorMessage, btnPrimary, btnSecondary, inputCls, labelCls, td, th,
} from "./trainingUi";

const KINDS: CourseKind[] = ["corso", "awareness", "phishing"];
const AUDIENCE_KINDS: AudienceKind[] = ["generale", "ruoli_critici", "organo_gestione"];

function ControlPicker({ value, onChange }: {
  value: ControlOption[]; onChange: (v: ControlOption[]) => void;
}) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const { data: options = [] } = useQuery({
    queryKey: ["training-control-options", search],
    queryFn: () => trainingApi.controlOptions(search),
    enabled: search.trim().length >= 2,
  });
  const chosen = new Set(value.map(c => c.id));

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {value.length === 0 && <span className="text-xs text-gray-400">{t("training.courses.no_controls")}</span>}
        {value.map(c => (
          <span key={c.id} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-800 text-xs px-2 py-0.5 rounded">
            {c.framework_code} {c.external_id}
            <button type="button" onClick={() => onChange(value.filter(v => v.id !== c.id))}
                    className="text-indigo-400 hover:text-indigo-700">×</button>
          </span>
        ))}
      </div>
      <input value={search} onChange={e => setSearch(e.target.value)}
             placeholder={t("training.courses.search_controls")} className={inputCls} />
      {search.trim().length >= 2 && (
        <div className="border border-gray-200 rounded mt-1 max-h-40 overflow-y-auto">
          {options.filter(o => !chosen.has(o.id)).length === 0 ? (
            <p className="text-xs text-gray-400 px-3 py-2">{t("training.courses.no_matches")}</p>
          ) : options.filter(o => !chosen.has(o.id)).map(o => (
            <button type="button" key={o.id} onClick={() => { onChange([...value, o]); setSearch(""); }}
                    className="block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50">
              <span className="font-medium">{o.framework_code} {o.external_id}</span>
              <span className="text-gray-500"> — {o.title}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CourseForm({ course, onClose }: { course?: TrainingCourse; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: course?.title ?? "",
    description: course?.description ?? "",
    kind: course?.kind ?? ("corso" as CourseKind),
    audience_kind: course?.audience_kind ?? ("generale" as AudienceKind),
    mandatory: course?.mandatory ?? true,
    validity_months: course ? course.validity_months : 12,
    duration_minutes: course?.duration_minutes ?? null,
    status: course?.status ?? "attivo",
  });
  const [controls, setControls] = useState<ControlOption[]>(course?.controls_detail ?? []);
  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm(f => ({ ...f, [k]: v }));

  const mutation = useMutation({
    mutationFn: () => {
      const payload = { ...form, controls: controls.map(c => c.id) };
      return course ? trainingApi.updateCourse(course.id, payload) : trainingApi.createCourse(payload);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["training-courses"] }); onClose(); },
  });

  return (
    <Modal title={course ? t("training.courses.edit") : t("training.courses.new")} onClose={onClose} wide>
      <div className="space-y-3">
        <div>
          <label className={labelCls}>{t("training.courses.fields.title")} *</label>
          <input value={form.title} onChange={e => set("title", e.target.value)} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>{t("training.courses.fields.description")}</label>
          <textarea value={form.description} onChange={e => set("description", e.target.value)} rows={2} className={inputCls} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>{t("training.courses.fields.kind")}</label>
            <select value={form.kind} onChange={e => set("kind", e.target.value as CourseKind)} className={inputCls}>
              {KINDS.map(k => <option key={k} value={k}>{t(`training.kinds.${k}`)}</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>{t("training.courses.fields.audience_kind")}</label>
            <select value={form.audience_kind} onChange={e => set("audience_kind", e.target.value as AudienceKind)} className={inputCls}>
              {AUDIENCE_KINDS.map(k => <option key={k} value={k}>{t(`training.audience_kinds.${k}`)}</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>{t("training.courses.fields.validity_months")}</label>
            <input type="number" min={1} value={form.validity_months ?? ""}
                   onChange={e => set("validity_months", e.target.value ? Number(e.target.value) : null)}
                   placeholder={t("training.courses.no_expiry")} className={inputCls} />
            <p className="text-xs text-gray-400 mt-1">{t("training.courses.validity_hint")}</p>
          </div>
          <div>
            <label className={labelCls}>{t("training.courses.fields.duration_minutes")}</label>
            <input type="number" min={1} value={form.duration_minutes ?? ""}
                   onChange={e => set("duration_minutes", e.target.value ? Number(e.target.value) : null)}
                   className={inputCls} />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={form.mandatory} onChange={e => set("mandatory", e.target.checked)} />
          {t("training.courses.fields.mandatory")}
        </label>
        {course && (
          <div>
            <label className={labelCls}>{t("training.courses.fields.status")}</label>
            <select value={form.status} onChange={e => set("status", e.target.value as "attivo" | "archiviato")} className={inputCls}>
              <option value="attivo">{t("training.statuses.attivo")}</option>
              <option value="archiviato">{t("training.statuses.archiviato")}</option>
            </select>
          </div>
        )}
        <div>
          <label className={labelCls}>{t("training.courses.fields.controls")}</label>
          <p className="text-xs text-gray-500 mb-2">{t("training.courses.controls_hint")}</p>
          <ControlPicker value={controls} onChange={setControls} />
        </div>
      </div>
      {mutation.isError && (
        <p className="text-sm text-red-600 mt-3">{apiErrorMessage(mutation.error, t("common.save_error"))}</p>
      )}
      <div className="flex justify-end gap-2 mt-5">
        <button onClick={onClose} className={btnSecondary}>{t("actions.cancel")}</button>
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.title.trim()} className={btnPrimary}>
          {mutation.isPending ? t("common.saving") : t("actions.save")}
        </button>
      </div>
    </Modal>
  );
}

export function CoursesTab({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<TrainingCourse | null>(null);
  const [creating, setCreating] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  const { data: courses = [], isLoading } = useQuery({
    queryKey: ["training-courses"],
    queryFn: () => trainingApi.courses(),
  });
  const remove = useMutation({
    mutationFn: (id: string) => trainingApi.deleteCourse(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["training-courses"] }),
    onError: (e) => alert(apiErrorMessage(e, t("common.save_error"))),
  });
  const rows = courses.filter(c => showArchived || c.status === "attivo");

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="text-sm text-gray-500">{t("training.courses.intro")}</p>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
            {t("training.courses.show_archived")}
          </label>
          {canManage && (
            <button onClick={() => setCreating(true)} className={btnPrimary}>{t("training.courses.new")}</button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("training.courses.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className={th}>{t("training.courses.fields.title")}</th>
                <th className={th}>{t("training.courses.fields.kind")}</th>
                <th className={th}>{t("training.courses.fields.audience_kind")}</th>
                <th className={th}>{t("training.courses.fields.validity_months")}</th>
                <th className={th}>{t("training.courses.fields.controls")}</th>
                <th className={th}>{t("training.courses.fields.status")}</th>
                {canManage && <th className={th} />}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className={td}>
                    <p className="font-medium text-gray-900">{c.title}</p>
                    {c.mandatory && <span className="text-xs text-red-700">{t("training.courses.fields.mandatory")}</span>}
                  </td>
                  <td className={`${td} text-gray-600`}>{t(`training.kinds.${c.kind}`)}</td>
                  <td className={`${td} text-gray-600`}>{t(`training.audience_kinds.${c.audience_kind}`)}</td>
                  <td className={`${td} text-gray-600`}>
                    {c.validity_months ?? t("training.courses.no_expiry")}
                  </td>
                  <td className={td}>
                    <div className="flex flex-wrap gap-1">
                      {c.controls_detail.length === 0 && <span className="text-xs text-amber-700">{t("training.courses.no_controls")}</span>}
                      {c.controls_detail.map(ctrl => (
                        <span key={ctrl.id} title={ctrl.title} className="text-xs bg-indigo-50 text-indigo-800 px-1.5 py-0.5 rounded">
                          {ctrl.external_id}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className={`${td} text-gray-600`}>{t(`training.statuses.${c.status}`)}</td>
                  {canManage && (
                    <td className={`${td} whitespace-nowrap text-right`}>
                      <button onClick={() => setEditing(c)} className="text-xs text-indigo-600 hover:text-indigo-800 mr-3">
                        {t("actions.edit")}
                      </button>
                      <button
                        onClick={() => window.confirm(t("training.courses.delete_confirm", { title: c.title })) && remove.mutate(c.id)}
                        className="text-xs text-red-600 hover:text-red-800">
                        {t("actions.delete")}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {creating && <CourseForm onClose={() => setCreating(false)} />}
      {editing && <CourseForm course={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
