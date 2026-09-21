import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { documentsApi } from "../../api/endpoints/documents";
import {
  courseAppliesTo,
  trainingApi,
  type TrainingAudience,
  type TrainingCapabilities,
  type TrainingCourse,
  type TrainingPlan,
} from "../../api/endpoints/training";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePlantToday } from "../../utils/dates";
import {
  CoverageBar, ItemStateBadge, Modal, apiErrorMessage, btnPrimary, btnSecondary, inputCls,
  labelCls, td, th,
} from "./trainingUi";

const invalidatePlans = (qc: ReturnType<typeof useQueryClient>) => {
  qc.invalidateQueries({ queryKey: ["training-plans"] });
  qc.invalidateQueries({ queryKey: ["training-plan-status"] });
};

function DocumentPicker({ plan, plantId, onClose }: { plan: TrainingPlan; plantId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const { data } = useQuery({
    queryKey: ["training-plan-docs", search, plantId],
    queryFn: () => documentsApi.searchDocuments(search, plan.plant ? plantId : undefined),
    enabled: search.trim().length >= 2,
  });
  const save = useMutation({
    mutationFn: (document: string | null) => trainingApi.updatePlan(plan.id, { document }),
    onSuccess: () => { invalidatePlans(qc); onClose(); },
  });

  return (
    <Modal title={t("training.plan.link_document")} onClose={onClose}>
      <p className="text-sm text-gray-500 mb-3">{t("training.plan.document_hint")}</p>
      <input value={search} onChange={e => setSearch(e.target.value)} className={inputCls}
             placeholder={t("training.plan.search_document")} />
      <div className="mt-2 max-h-60 overflow-y-auto divide-y divide-gray-100">
        {(data?.results ?? []).map(d => (
          <button key={d.id} onClick={() => save.mutate(d.id)}
                  className="w-full text-left px-2 py-2 text-sm hover:bg-gray-50 flex items-center justify-between gap-2">
            <span>{d.document_code ? `${d.document_code} — ` : ""}{d.title}</span>
            <StatusBadge status={d.status} />
          </button>
        ))}
      </div>
      {save.isError && <p className="text-sm text-red-600 mt-2">{apiErrorMessage(save.error, t("common.save_error"))}</p>}
      <div className="flex justify-between mt-4">
        {plan.document ? (
          <button onClick={() => save.mutate(null)} className="text-sm text-red-600 hover:text-red-800">
            {t("training.plan.unlink_document")}
          </button>
        ) : <span />}
        <button onClick={onClose} className={btnSecondary}>{t("actions.cancel")}</button>
      </div>
    </Modal>
  );
}

function ItemForm({ plan, courses, audiences, onClose }: {
  plan: TrainingPlan; courses: TrainingCourse[]; audiences: TrainingAudience[]; onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [course, setCourse] = useState("");
  const [due, setDue] = useState(`${plan.year}-12-31`);
  const [chosen, setChosen] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const selectedCourse = courses.find(c => c.id === course);
  const phishing = selectedCourse?.kind === "phishing";

  const save = useMutation({
    mutationFn: () => trainingApi.createPlanItem({ plan: plan.id, course, due_date: due, audiences: chosen, notes }),
    onSuccess: () => { invalidatePlans(qc); onClose(); },
  });
  const toggle = (id: string) => setChosen(c => (c.includes(id) ? c.filter(x => x !== id) : [...c, id]));

  return (
    <Modal title={t("training.plan.add_item")} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className={labelCls}>{t("training.plan.fields.course")} *</label>
          <select value={course} onChange={e => setCourse(e.target.value)} className={inputCls}>
            <option value="">—</option>
            {courses.filter(c => c.status === "attivo" && courseAppliesTo(c, plan.plant)).map(c => (
              <option key={c.id} value={c.id}>{c.title} · {t(`training.kinds.${c.kind}`)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelCls}>{t("training.plan.fields.due_date")} *</label>
          <input type="date" value={due} onChange={e => setDue(e.target.value)} className={inputCls} />
        </div>
        {!phishing && (
          <div>
            <label className={labelCls}>{t("training.plan.fields.audiences")}</label>
            {audiences.length === 0 ? (
              <p className="text-xs text-amber-700">{t("training.plan.no_audiences")}</p>
            ) : (
              <div className="space-y-1">
                {audiences.map(a => (
                  <label key={a.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={chosen.includes(a.id)} onChange={() => toggle(a.id)} />
                    {a.name} <span className="text-gray-400">({a.headcount})</span>
                  </label>
                ))}
              </div>
            )}
            <p className="text-xs text-gray-400 mt-1">{t("training.plan.audiences_hint")}</p>
          </div>
        )}
        <div>
          <label className={labelCls}>{t("training.plan.fields.notes")}</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} className={inputCls} />
        </div>
      </div>
      {save.isError && <p className="text-sm text-red-600 mt-3">{apiErrorMessage(save.error, t("common.save_error"))}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button onClick={onClose} className={btnSecondary}>{t("actions.cancel")}</button>
        <button onClick={() => save.mutate()} disabled={save.isPending || !course || !due} className={btnPrimary}>
          {save.isPending ? t("common.saving") : t("actions.save")}
        </button>
      </div>
    </Modal>
  );
}

function PlanBlock({ plan, plantId, canManage, courses, audiences }: {
  plan: TrainingPlan; plantId: string; canManage: boolean;
  courses: TrainingCourse[]; audiences: TrainingAudience[];
}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [pickingDoc, setPickingDoc] = useState(false);
  const { data: status } = useQuery({
    queryKey: ["training-plan-status", plan.id],
    queryFn: () => trainingApi.planStatus(plan.id),
  });
  const removeItem = useMutation({
    mutationFn: (id: string) => trainingApi.deletePlanItem(id),
    onSuccess: () => invalidatePlans(qc),
    onError: (e) => alert(apiErrorMessage(e, t("common.save_error"))),
  });
  const counts = status?.counts;

  return (
    <div className="bg-white border border-gray-200 rounded-lg mb-5">
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 border-b border-gray-100">
        <div>
          <h3 className="font-semibold text-gray-900">
            {plan.plant ? t("training.plan.site_plan", { code: plan.plant_code, year: plan.year })
                        : t("training.plan.org_plan", { year: plan.year })}
          </h3>
          <div className="flex flex-wrap items-center gap-2 mt-1 text-sm">
            <span className="text-gray-500">{t("training.plan.document")}:</span>
            {plan.document ? (
              <>
                <span className="text-gray-800">{plan.document_title}</span>
                {plan.document_status && <StatusBadge status={plan.document_status} />}
              </>
            ) : (
              <span className="text-amber-700">{t("training.plan.no_document")}</span>
            )}
            {canManage && (
              <button onClick={() => setPickingDoc(true)} className="text-xs text-indigo-600 hover:text-indigo-800">
                {plan.document ? t("actions.edit") : t("training.plan.link_document")}
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {counts && (
            <div className="flex gap-1.5 text-xs">
              {(["fatto", "in_scadenza", "in_ritardo", "pianificato"] as const).map(s => counts[s] > 0 && (
                <span key={s} className="flex items-center gap-1"><ItemStateBadge state={s} /> {counts[s]}</span>
              ))}
            </div>
          )}
          {canManage && <button onClick={() => setAdding(true)} className={btnPrimary}>{t("training.plan.add_item")}</button>}
        </div>
      </div>

      {!status ? (
        <div className="p-6 text-center text-gray-400 text-sm">{t("common.loading")}</div>
      ) : status.items.length === 0 ? (
        <div className="p-6 text-center text-gray-400 text-sm">{t("training.plan.empty_items")}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className={th}>{t("training.plan.fields.course")}</th>
                <th className={th}>{t("training.plan.fields.due_date")}</th>
                <th className={th}>{t("training.plan.fields.state")}</th>
                <th className={`${th} text-right`}>{t("training.plan.fields.sessions")}</th>
                <th className={th}>{t("training.plan.fields.coverage")}</th>
                {canManage && <th className={th} />}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {status.items.map(it => (
                <tr key={it.item_id} className="hover:bg-gray-50">
                  <td className={`${td} font-medium text-gray-900`}>{it.course_title}</td>
                  <td className={`${td} text-gray-600 whitespace-nowrap`}>{new Date(it.due_date).toLocaleDateString(i18n.language)}</td>
                  <td className={td}><ItemStateBadge state={it.state} /></td>
                  <td className={`${td} text-right`}>{it.sessions}</td>
                  <td className={td}>
                    {it.target_count
                      ? <div><CoverageBar pct={it.coverage_pct} />
                          <p className="text-xs text-gray-400 mt-0.5">{it.trained_count}/{it.target_count}</p></div>
                      : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  {canManage && (
                    <td className={`${td} text-right`}>
                      {it.sessions === 0 && (
                        <button onClick={() => window.confirm(t("training.plan.delete_item_confirm")) && removeItem.mutate(it.item_id)}
                                className="text-xs text-red-600 hover:text-red-800">
                          {t("actions.delete")}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {adding && (
        <ItemForm plan={plan} courses={courses} audiences={audiences} onClose={() => setAdding(false)} />
      )}
      {pickingDoc && <DocumentPicker plan={plan} plantId={plantId} onClose={() => setPickingDoc(false)} />}
    </div>
  );
}

export function PlanTab({ plantId, caps }: { plantId: string; caps: TrainingCapabilities }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const thisYear = Number(usePlantToday().slice(0, 4));
  const [year, setYear] = useState(thisYear);
  const canManageSite = caps.manage_plant_ids.includes(plantId);

  const { data: plans = [], isLoading } = useQuery({
    queryKey: ["training-plans", year],
    queryFn: () => trainingApi.plans({ year: String(year) }),
  });
  const { data: courses = [] } = useQuery({
    queryKey: ["training-courses"],
    queryFn: () => trainingApi.courses(),
    select: cs => cs.filter(c => c.status === "attivo"),
  });
  const { data: audiences = [] } = useQuery({
    queryKey: ["training-audiences", plantId],
    queryFn: () => trainingApi.audiences({ plant: plantId }),
  });
  const create = useMutation({
    mutationFn: (plant: string | null) => trainingApi.createPlan({ plant, year }),
    onSuccess: () => invalidatePlans(qc),
    onError: (e) => alert(apiErrorMessage(e, t("common.save_error"))),
  });

  const sitePlan = plans.find(p => p.plant === plantId);
  const orgPlan = plans.find(p => p.plant === null);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <p className="text-sm text-gray-500 max-w-3xl">{t("training.plan.intro")}</p>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">{t("training.plan.year")}</label>
          <select value={year} onChange={e => setYear(Number(e.target.value))} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
            {[thisYear - 1, thisYear, thisYear + 1].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
      ) : (
        <>
          {sitePlan ? (
            <PlanBlock plan={sitePlan} plantId={plantId} canManage={canManageSite} courses={courses} audiences={audiences} />
          ) : (
            <div className="bg-white border border-dashed border-gray-300 rounded-lg p-6 text-center mb-5">
              <p className="text-sm text-gray-500">{t("training.plan.no_site_plan", { year })}</p>
              {canManageSite && (
                <button onClick={() => create.mutate(plantId)} disabled={create.isPending} className={`${btnPrimary} mt-3`}>
                  {t("training.plan.create_site", { year })}
                </button>
              )}
            </div>
          )}
          {orgPlan ? (
            <PlanBlock plan={orgPlan} plantId={plantId} canManage={caps.can_manage_org} courses={courses} audiences={audiences} />
          ) : caps.can_manage_org && (
            <button onClick={() => create.mutate(null)} disabled={create.isPending} className={btnSecondary}>
              {t("training.plan.create_org", { year })}
            </button>
          )}
        </>
      )}
    </div>
  );
}
