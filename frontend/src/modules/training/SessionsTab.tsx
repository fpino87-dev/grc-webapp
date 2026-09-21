import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  courseAppliesTo,
  isNamedCourse,
  trainingApi,
  type ParticipantOptions,
  type SessionCreated,
  type TrainingSession,
} from "../../api/endpoints/training";
import { downloadEvidenceFile } from "../../components/ui/EvidencePreviewModal";
import { usePlantToday } from "../../utils/dates";
import {
  Modal, apiErrorMessage, btnPrimary, btnSecondary, inputCls, labelCls, td, th,
} from "./trainingUi";

const invalidate = (qc: ReturnType<typeof useQueryClient>) => {
  for (const key of ["training-sessions", "training-plans", "training-plan-status", "training-board"]) {
    qc.invalidateQueries({ queryKey: [key] });
  }
};

// Ruoli critici e organo di gestione: si sceglie chi ha partecipato fra chi è
// in carica sul sito alla data dell'erogazione.
function ParticipantPicker({ options, users, members, onUsers, onMembers }: {
  options: ParticipantOptions | undefined;
  users: string[]; members: string[];
  onUsers: (v: string[]) => void; onMembers: (v: string[]) => void;
}) {
  const { t } = useTranslation();
  const flip = (list: string[], id: string) => (list.includes(id) ? list.filter(x => x !== id) : [...list, id]);
  if (!options) return <p className="text-xs text-gray-400">{t("common.loading")}</p>;
  const box = "border border-gray-200 rounded p-2 max-h-48 overflow-y-auto space-y-1";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">{t("training.sessions.participants.role_holders")}</p>
        <div className={box}>
          {options.role_holders.length === 0 && (
            <p className="text-xs text-gray-400">{t("training.sessions.participants.no_role_holders")}</p>
          )}
          {options.role_holders.map(h => (
            <label key={h.user_id} className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={users.includes(h.user_id)}
                     onChange={() => onUsers(flip(users, h.user_id))} />
              <span>
                {h.name}
                <span className="block text-xs text-gray-400">
                  {h.roles.map(r => t(`governance.roles.${r}`, { defaultValue: r })).join(", ")}
                </span>
              </span>
            </label>
          ))}
        </div>
      </div>
      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">{t("training.sessions.participants.members")}</p>
        <div className={box}>
          {options.members.length === 0 && (
            <p className="text-xs text-gray-400">{t("training.sessions.participants.no_members")}</p>
          )}
          {options.members.map(m => (
            <label key={m.member_id} className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={members.includes(m.member_id)}
                     onChange={() => onMembers(flip(members, m.member_id))} />
              <span>
                {m.name}
                {m.management_body && (
                  <span className="ml-1 text-[10px] bg-indigo-50 text-indigo-700 px-1 rounded">
                    {t("training.sessions.participants.management_body")}
                  </span>
                )}
                <span className="block text-xs text-gray-400">
                  {[m.position, m.committee].filter(Boolean).join(" · ")}
                </span>
              </span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

function SessionForm({ plantId, onClose, onDone }: {
  plantId: string; onClose: () => void; onDone: (s: SessionCreated) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const today = usePlantToday();
  const [course, setCourse] = useState("");
  const [heldOn, setHeldOn] = useState(today);
  const [planItem, setPlanItem] = useState("");
  const [chosen, setChosen] = useState<string[]>([]);
  const [counts, setCounts] = useState({ target: "", trained: "", sent: "", clicked: "", reported: "" });
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [users, setUsers] = useState<string[]>([]);
  const [members, setMembers] = useState<string[]>([]);

  const { data: courses = [] } = useQuery({
    queryKey: ["training-courses"],
    queryFn: () => trainingApi.courses(),
    // Corsi attivi validi per il sito: di organizzazione o di questo sito.
    select: cs => cs.filter(c => c.status === "attivo" && courseAppliesTo(c, plantId)),
  });
  const { data: audiences = [] } = useQuery({
    queryKey: ["training-audiences", plantId],
    queryFn: () => trainingApi.audiences({ plant: plantId }),
  });
  const year = heldOn.slice(0, 4);
  const { data: plans = [] } = useQuery({
    queryKey: ["training-plans", Number(year)],
    queryFn: () => trainingApi.plans({ year }),
    enabled: year.length === 4,
  });
  const { data: items = [] } = useQuery({
    queryKey: ["training-plan-items", course],
    queryFn: () => trainingApi.planItems({ course }),
    enabled: !!course,
  });

  const selected = courses.find(c => c.id === course);
  const phishing = selected?.kind === "phishing";
  const named = !!selected && isNamedCourse(selected);
  const { data: options } = useQuery({
    queryKey: ["training-participant-options", plantId, heldOn],
    queryFn: () => trainingApi.participantOptions(plantId, heldOn),
    enabled: named && heldOn.length === 10,
  });
  // Una persona scelta sia come componente sia come titolare di nomine conta una volta.
  const people = useMemo(() => {
    const keys = new Set(users);
    for (const id of members) {
      const m = options?.members.find(x => x.member_id === id);
      keys.add(m?.user_id ?? id);
    }
    return keys.size;
  }, [users, members, options]);
  const planIds = new Set(plans.filter(p => p.plant === plantId || p.plant === null).map(p => p.id));
  const eligibleItems = items.filter(i => planIds.has(i.plan));
  const headcount = useMemo(
    () => audiences.filter(a => chosen.includes(a.id)).reduce((n, a) => n + a.headcount, 0),
    [audiences, chosen],
  );
  const setCount = (k: keyof typeof counts, v: string) => setCounts(c => ({ ...c, [k]: v }));
  const toggle = (id: string) => setChosen(c => (c.includes(id) ? c.filter(x => x !== id) : [...c, id]));

  const save = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("course", course);
      form.append("plant", plantId);
      form.append("held_on", heldOn);
      if (planItem) form.append("plan_item", planItem);
      if (named) {
        users.forEach(u => form.append("participant_users", u));
        members.forEach(m => form.append("participant_members", m));
      } else {
        chosen.forEach(a => form.append("audiences", a));
      }
      const numbers: [string, string][] = phishing
        ? [["sent_count", counts.sent], ["clicked_count", counts.clicked], ["reported_count", counts.reported]]
        : named
          ? [["target_count", counts.target]]
          : [["target_count", counts.target], ["trained_count", counts.trained]];
      numbers.forEach(([k, v]) => v !== "" && form.append(k, v));
      if (notes) form.append("notes", notes);
      if (file) form.append("file", file);
      return trainingApi.registerSession(form);
    },
    onSuccess: (s) => { invalidate(qc); onDone(s); },
  });

  const ready = course && heldOn && file
    && (phishing ? counts.sent !== "" : named ? people > 0 : counts.trained !== "");

  return (
    <Modal title={t("training.sessions.new")} onClose={onClose} wide>
      <div className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>{t("training.sessions.fields.course")} *</label>
            <select value={course} onChange={e => { setCourse(e.target.value); setPlanItem(""); }} className={inputCls}>
              <option value="">—</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.title} · {t(`training.kinds.${c.kind}`)}</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>{t("training.sessions.fields.held_on")} *</label>
            <input type="date" max={today} value={heldOn} onChange={e => setHeldOn(e.target.value)} className={inputCls} />
          </div>
        </div>
        {course && (
          <div>
            <label className={labelCls}>{t("training.sessions.fields.plan_item")}</label>
            <select value={planItem} onChange={e => setPlanItem(e.target.value)} className={inputCls}>
              <option value="">{t("training.sessions.plan_item_auto")}</option>
              {eligibleItems.map(i => (
                <option key={i.id} value={i.id}>{t("training.sessions.plan_item_option", { due: i.due_date })}</option>
              ))}
            </select>
          </div>
        )}
        {named && (
          <div>
            <label className={labelCls}>{t("training.sessions.fields.participants")} *</label>
            <p className="text-xs text-gray-500 mb-2">
              {t("training.sessions.participants.hint")}
              {selected?.competency && (
                <> {t("training.sessions.participants.competency_hint", { competency: selected.competency, level: selected.competency_level })}</>
              )}
            </p>
            <ParticipantPicker options={options} users={users} members={members}
                               onUsers={setUsers} onMembers={setMembers} />
          </div>
        )}
        {!phishing && !named && (
          <div>
            <label className={labelCls}>{t("training.sessions.fields.audiences")}</label>
            {audiences.length === 0 ? (
              <p className="text-xs text-amber-700">{t("training.plan.no_audiences")}</p>
            ) : (
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {audiences.map(a => (
                  <label key={a.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={chosen.includes(a.id)} onChange={() => toggle(a.id)} />
                    {a.name} <span className="text-gray-400">({a.headcount})</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
        {named ? (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>{t("training.sessions.fields.target")}</label>
              <input type="number" min={0} value={counts.target} onChange={e => setCount("target", e.target.value)}
                     placeholder={people ? String(people) : ""} className={inputCls} />
              <p className="text-xs text-gray-400 mt-1">{t("training.sessions.participants.target_hint")}</p>
            </div>
            <div>
              <label className={labelCls}>{t("training.sessions.fields.trained")}</label>
              <p className="text-sm text-gray-700 py-2">{people}</p>
            </div>
          </div>
        ) : phishing ? (
          <div className="grid grid-cols-3 gap-3">
            {(["sent", "clicked", "reported"] as const).map(k => (
              <div key={k}>
                <label className={labelCls}>{t(`training.sessions.fields.${k}`)}{k === "sent" ? " *" : ""}</label>
                <input type="number" min={0} value={counts[k]} onChange={e => setCount(k, e.target.value)} className={inputCls} />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>{t("training.sessions.fields.target")}</label>
              <input type="number" min={0} value={counts.target} onChange={e => setCount("target", e.target.value)}
                     placeholder={headcount ? String(headcount) : ""} className={inputCls} />
              <p className="text-xs text-gray-400 mt-1">{t("training.sessions.target_hint")}</p>
            </div>
            <div>
              <label className={labelCls}>{t("training.sessions.fields.trained")} *</label>
              <input type="number" min={0} value={counts.trained} onChange={e => setCount("trained", e.target.value)} className={inputCls} />
            </div>
          </div>
        )}
        <div>
          <label className={labelCls}>{t("training.sessions.fields.file")} *</label>
          <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
          <p className="text-xs text-gray-400 mt-1">{t("training.sessions.file_hint")}</p>
        </div>
        <div>
          <label className={labelCls}>{t("training.sessions.fields.notes")}</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} className={inputCls} />
        </div>
      </div>
      {save.isError && <p className="text-sm text-red-600 mt-3">{apiErrorMessage(save.error, t("common.save_error"))}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button onClick={onClose} className={btnSecondary}>{t("actions.cancel")}</button>
        <button onClick={() => save.mutate()} disabled={save.isPending || !ready} className={btnPrimary}>
          {save.isPending ? t("common.saving") : t("training.sessions.register")}
        </button>
      </div>
    </Modal>
  );
}

function Counts({ s }: { s: TrainingSession }) {
  const { t } = useTranslation();
  if (s.course_kind === "phishing") {
    return (
      <span className="text-xs text-gray-600">
        {t("training.sessions.phishing_counts", { sent: s.sent_count ?? 0, clicked: s.clicked_count ?? 0, reported: s.reported_count ?? 0 })}
      </span>
    );
  }
  return <span className="text-sm">{s.trained_count ?? "—"}/{s.target_count ?? "—"}</span>;
}

// NIS2 art. 20: chi siede nell'organo di gestione e fino a quando la sua
// formazione è valida. Nascosto se il sito non ha un CdA in anagrafica.
function BoardCard({ plantId }: { plantId: string }) {
  const { t, i18n } = useTranslation();
  const { data } = useQuery({
    queryKey: ["training-board", plantId],
    queryFn: () => trainingApi.boardStatus(plantId),
  });
  if (!data || data.total === 0) return null;
  const fmt = (d: string) => new Date(d).toLocaleDateString(i18n.language);
  const allOk = data.trained === data.total;

  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 mb-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
        <p className="text-sm font-medium text-gray-800">{t("training.board.title")}</p>
        <p className={`text-sm font-semibold ${allOk ? "text-green-700" : "text-amber-700"}`}>
          {t("training.board.summary", { trained: data.trained, total: data.total })}
        </p>
      </div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs">
        {data.members.map(m => (
          <li key={m.member_id} className="flex items-center gap-1.5" title={m.committee}>
            <span className={`w-2 h-2 rounded-full ${m.trained ? "bg-green-500" : "bg-red-500"}`} />
            <span className="text-gray-700">{m.full_name}</span>
            <span className="text-gray-400">
              {m.trained
                ? (m.valid_until ? t("training.board.valid_until", { date: fmt(m.valid_until) }) : t("training.board.no_expiry"))
                : t("training.board.to_train")}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-gray-400 mt-2">{t("training.board.hint")}</p>
    </div>
  );
}

export function SessionsTab({ plantId, canManage }: { plantId: string; canManage: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<SessionCreated | null>(null);
  const today = usePlantToday();

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["training-sessions", plantId],
    queryFn: () => trainingApi.sessions({ plant: plantId }),
  });
  const { data: audiences = [] } = useQuery({
    queryKey: ["training-audiences", plantId],
    queryFn: () => trainingApi.audiences({ plant: plantId }),
  });
  const names = new Map(audiences.map(a => [a.id, a.name]));
  const remove = useMutation({
    mutationFn: (id: string) => trainingApi.deleteSession(id),
    onSuccess: () => invalidate(qc),
    onError: (e) => alert(apiErrorMessage(e, t("common.save_error"))),
  });
  const fmt = (d: string) => new Date(d).toLocaleDateString(i18n.language);

  async function download(s: TrainingSession) {
    if (!s.evidence) return;
    try {
      await downloadEvidenceFile({ id: s.evidence, title: s.course_title, file_path: s.evidence_file_path });
    } catch {
      alert(t("documents.errors.evidence_download_failed"));
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="text-sm text-gray-500 max-w-3xl">{t("training.sessions.intro")}</p>
        {canManage && <button onClick={() => setCreating(true)} className={btnPrimary}>{t("training.sessions.new")}</button>}
      </div>

      {result && (
        <div className="bg-green-50 border border-green-200 rounded px-4 py-3 mb-3 text-sm flex justify-between gap-3">
          <div>
            <p className="text-green-800">{t("training.sessions.registered", { count: result.control_links.linked })}</p>
            {result.control_links.not_applicable.length > 0 && (
              <p className="text-amber-700 mt-1">
                {t("training.sessions.not_applicable", { codes: result.control_links.not_applicable.join(", ") })}
              </p>
            )}
          </div>
          <button onClick={() => setResult(null)} className="text-gray-400 hover:text-gray-600">×</button>
        </div>
      )}

      <BoardCard plantId={plantId} />

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : sessions.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("training.sessions.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className={th}>{t("training.sessions.fields.held_on")}</th>
                <th className={th}>{t("training.sessions.fields.course")}</th>
                <th className={th}>{t("training.sessions.fields.audiences")}</th>
                <th className={th}>{t("training.sessions.fields.counts")}</th>
                <th className={th}>{t("training.sessions.fields.proof")}</th>
                {canManage && <th className={th} />}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className={`${td} whitespace-nowrap text-gray-600`}>{fmt(s.held_on)}</td>
                  <td className={td}>
                    <p className="font-medium text-gray-900">{s.course_title}</p>
                    <p className="text-xs text-gray-500">{t(`training.kinds.${s.course_kind}`)}</p>
                  </td>
                  <td className={`${td} text-xs text-gray-600`}>
                    {s.participants_detail.length > 0
                      ? s.participants_detail.map(p => p.name).join(", ")
                      : s.audiences.map(a => names.get(a) ?? "").filter(Boolean).join(", ") || "—"}
                  </td>
                  <td className={td}><Counts s={s} /></td>
                  <td className={td}>
                    {s.legacy ? (
                      <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t("training.sessions.legacy")}</span>
                    ) : s.evidence ? (
                      <div>
                        <button onClick={() => download(s)} className="text-xs text-indigo-600 hover:text-indigo-800">
                          {t("training.sessions.download")}
                        </button>
                        {s.evidence_valid_until && (
                          <p className={`text-xs mt-0.5 ${s.evidence_valid_until < today ? "text-red-600" : "text-gray-400"}`}>
                            {t("training.sessions.valid_until", { date: fmt(s.evidence_valid_until) })}
                          </p>
                        )}
                      </div>
                    ) : "—"}
                  </td>
                  {canManage && (
                    <td className={`${td} text-right`}>
                      {!s.legacy && (
                        <button onClick={() => window.confirm(t("training.sessions.delete_confirm")) && remove.mutate(s.id)}
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
        )}
      </div>

      {creating && (
        <SessionForm plantId={plantId} onClose={() => setCreating(false)}
                     onDone={(s) => { setResult(s); setCreating(false); }} />
      )}
    </div>
  );
}
