import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { plantsApi } from "../../api/endpoints/plants";
import {
  isNamedCourse,
  trainingApi,
  type AudienceKind,
  type ControlOption,
  type CourseKind,
  type TrainingCapabilities,
  type TrainingCourse,
} from "../../api/endpoints/training";
import {
  Modal, apiErrorMessage, btnPrimary, btnSecondary, inputCls, labelCls, td, th,
} from "./trainingUi";

const KINDS: CourseKind[] = ["corso", "awareness", "phishing"];
const AUDIENCE_KINDS: AudienceKind[] = ["generale", "ruoli_critici", "organo_gestione"];

// Cerca un controllo per codice (es. «PR.AT-01») fra quelli dei framework caricati.
function ControlSearch({ exclude, onPick }: {
  exclude: Set<string>; onPick: (c: ControlOption) => void;
}) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const { data: options = [] } = useQuery({
    queryKey: ["training-control-options", search],
    queryFn: () => trainingApi.controlOptions(search),
    enabled: search.trim().length >= 2,
  });
  const available = options.filter(o => !exclude.has(o.id));

  return (
    <div className="relative">
      <input value={search} onChange={e => setSearch(e.target.value)} autoFocus
             placeholder={t("training.evidence_controls.search")} className={inputCls} />
      {search.trim().length >= 2 && (
        <div className="absolute z-10 w-full bg-white border border-gray-200 rounded mt-1 max-h-48 overflow-y-auto shadow">
          {available.length === 0 ? (
            <p className="text-xs text-gray-400 px-3 py-2">{t("training.evidence_controls.no_matches")}</p>
          ) : available.map(o => (
            <button type="button" key={o.id} onClick={() => { onPick(o); setSearch(""); }}
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

// Quali controlli prova un'erogazione, per tipo di destinatari: vale per tutti
// i corsi e tutti i siti; la prova va solo sui framework applicati al sito.
function EvidenceControlsPanel({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [adding, setAdding] = useState<AudienceKind | null>(null);
  const { data: rules = [] } = useQuery({
    queryKey: ["training-evidence-controls"],
    queryFn: () => trainingApi.evidenceControls(),
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ["training-evidence-controls"] });
  const onError = (e: unknown) => alert(apiErrorMessage(e, t("common.save_error")));
  const add = useMutation({
    mutationFn: ({ kind, control }: { kind: AudienceKind; control: string }) =>
      trainingApi.createEvidenceControl(kind, control),
    onSuccess: refresh, onError,
  });
  const remove = useMutation({
    mutationFn: (id: string) => trainingApi.deleteEvidenceControl(id),
    onSuccess: refresh, onError,
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 mb-4">
      <p className="text-sm font-medium text-gray-800">{t("training.evidence_controls.title")}</p>
      <p className="text-xs text-gray-500 mb-3">{t("training.evidence_controls.intro")}</p>
      <div className="space-y-2">
        {AUDIENCE_KINDS.map(kind => {
          const own = rules.filter(r => r.audience_kind === kind);
          return (
            <div key={kind} className="grid grid-cols-1 sm:grid-cols-[12rem_1fr] gap-2 items-start">
              <p className="text-sm text-gray-700 pt-0.5">{t(`training.audience_kinds.${kind}`)}</p>
              <div>
                <div className="flex flex-wrap items-center gap-1.5">
                  {own.length === 0 && (
                    <span className="text-xs text-gray-400">
                      {t(kind === "organo_gestione" ? "training.evidence_controls.none_board" : "training.evidence_controls.none")}
                    </span>
                  )}
                  {own.map(r => (
                    <span key={r.id} title={r.control_detail.title}
                          className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-800 text-xs px-2 py-0.5 rounded">
                      {r.control_detail.framework_code} {r.control_detail.external_id}
                      {canEdit && (
                        <button type="button" onClick={() => remove.mutate(r.id)}
                                aria-label={t("actions.delete")}
                                className="text-indigo-400 hover:text-indigo-700">×</button>
                      )}
                    </span>
                  ))}
                  {canEdit && adding !== kind && (
                    <button type="button" onClick={() => setAdding(kind)}
                            className="text-xs text-indigo-600 hover:text-indigo-800">
                      + {t("training.evidence_controls.add")}
                    </button>
                  )}
                </div>
                {canEdit && adding === kind && (
                  <div className="flex gap-2 mt-2 max-w-md">
                    <div className="flex-1">
                      <ControlSearch exclude={new Set(own.map(r => r.control))}
                                     onPick={c => { add.mutate({ kind, control: c.id }); setAdding(null); }} />
                    </div>
                    <button type="button" onClick={() => setAdding(null)} className={btnSecondary}>
                      {t("actions.cancel")}
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Chi può modificare un corso: di organizzazione → perimetro di organizzazione;
// di sito → chi gestisce tutti i suoi siti (lo ricontrolla il backend).
const canEditCourse = (c: TrainingCourse, caps: TrainingCapabilities) =>
  c.plants.length === 0 ? caps.can_manage_org : c.plants.every(id => caps.manage_plant_ids.includes(id));

function CourseForm({ course, caps, onClose }: {
  course?: TrainingCourse; caps: TrainingCapabilities; onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [orgWide, setOrgWide] = useState(course ? course.plants.length === 0 : caps.can_manage_org);
  const [sites, setSites] = useState<string[]>(course?.plants ?? []);
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: plantsApi.list });
  const manageable = plants.filter(p => caps.manage_plant_ids.includes(p.id));
  const [form, setForm] = useState({
    title: course?.title ?? "",
    description: course?.description ?? "",
    kind: course?.kind ?? ("corso" as CourseKind),
    audience_kind: course?.audience_kind ?? ("generale" as AudienceKind),
    mandatory: course?.mandatory ?? true,
    validity_months: course ? course.validity_months : 12,
    duration_minutes: course?.duration_minutes ?? null,
    status: course?.status ?? "attivo",
    competency: course?.competency ?? "",
    competency_level: course?.competency_level ?? (1 as 1 | 2 | 3),
  });
  const named = isNamedCourse(form);
  const { data: competencies = [] } = useQuery({
    queryKey: ["training-competency-options"],
    queryFn: () => trainingApi.competencyOptions(),
    enabled: named,
  });
  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm(f => ({ ...f, [k]: v }));

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        ...form,
        competency: named ? form.competency.trim() : "",
        plants: orgWide ? [] : sites,
      };
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
        {named && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <label className={labelCls}>{t("training.courses.fields.competency")}</label>
              <input value={form.competency} onChange={e => set("competency", e.target.value)}
                     list="training-competencies" className={inputCls} />
              <datalist id="training-competencies">
                {competencies.map(c => <option key={c} value={c} />)}
              </datalist>
            </div>
            <div>
              <label className={labelCls}>{t("training.courses.fields.competency_level")}</label>
              <select value={form.competency_level}
                      onChange={e => set("competency_level", Number(e.target.value) as 1 | 2 | 3)}
                      className={inputCls}>
                {([1, 2, 3] as const).map(l => (
                  <option key={l} value={l}>{t(`training.competency_levels.${l}`)}</option>
                ))}
              </select>
            </div>
            <p className="sm:col-span-3 text-xs text-gray-400 -mt-1">{t("training.courses.competency_hint")}</p>
          </div>
        )}
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
          <label className={labelCls}>{t("training.courses.fields.scope")}</label>
          <div className="space-y-1">
            <label className={`flex items-center gap-2 text-sm ${caps.can_manage_org ? "text-gray-700" : "text-gray-400"}`}>
              <input type="radio" checked={orgWide} disabled={!caps.can_manage_org} onChange={() => setOrgWide(true)} />
              {t("training.courses.scope_org")}
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="radio" checked={!orgWide} onChange={() => setOrgWide(false)} />
              {t("training.courses.scope_sites")}
            </label>
          </div>
          {!orgWide && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 ml-6">
              {manageable.map(p => (
                <label key={p.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={sites.includes(p.id)}
                         onChange={() => setSites(v => (v.includes(p.id) ? v.filter(x => x !== p.id) : [...v, p.id]))} />
                  {p.code} <span className="text-gray-400">{p.name}</span>
                </label>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-400 mt-1">{t("training.courses.scope_hint")}</p>
        </div>
      </div>
      {mutation.isError && (
        <p className="text-sm text-red-600 mt-3">{apiErrorMessage(mutation.error, t("common.save_error"))}</p>
      )}
      <div className="flex justify-end gap-2 mt-5">
        <button onClick={onClose} className={btnSecondary}>{t("actions.cancel")}</button>
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.title.trim() || (!orgWide && sites.length === 0)}
                className={btnPrimary}>
          {mutation.isPending ? t("common.saving") : t("actions.save")}
        </button>
      </div>
    </Modal>
  );
}

export function CoursesTab({ caps }: { caps: TrainingCapabilities }) {
  const canManage = caps.can_manage_courses;
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

      {caps.can_read_records && <EvidenceControlsPanel canEdit={caps.can_manage_org} />}

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
                <th className={th}>{t("training.courses.fields.scope")}</th>
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
                  <td className={`${td} text-gray-600`}>
                    {t(`training.audience_kinds.${c.audience_kind}`)}
                    {isNamedCourse(c) && c.competency && (
                      <p className="text-xs text-gray-400">
                        {t("training.courses.grants", { competency: c.competency, level: c.competency_level })}
                      </p>
                    )}
                  </td>
                  <td className={`${td} text-gray-600`}>
                    {c.validity_months ?? t("training.courses.no_expiry")}
                  </td>
                  <td className={`${td} text-gray-600`}>
                    {c.plant_codes.length === 0 ? t("training.courses.scope_org_short") : c.plant_codes.join(", ")}
                  </td>
                  <td className={`${td} text-gray-600`}>{t(`training.statuses.${c.status}`)}</td>
                  {canManage && !canEditCourse(c, caps) && <td className={td} />}
                  {canManage && canEditCourse(c, caps) && (
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

      {creating && <CourseForm caps={caps} onClose={() => setCreating(false)} />}
      {editing && <CourseForm course={editing} caps={caps} onClose={() => setEditing(null)} />}
    </div>
  );
}
