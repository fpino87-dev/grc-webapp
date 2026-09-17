import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  managementReviewApi, reviewErrorMessage,
  type DecisionType, type ManagementReview, type ReviewAction, type ReviewAgendaItem,
} from "../../api/endpoints/managementReview";
import { GRC_ACCESS_ROLES, type GrcUser } from "../../api/endpoints/users";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AGENDA_CODES_WITH_DATA, AgendaData } from "./SnapshotBlocks";
import { ISO_CLAUSE, fmtDate, isOverdue, userLabel, type Snap } from "./shared";

const DECISION_TYPES: DecisionType[] = ["miglioramento", "modifica_sgsi", "risorse", "altro"];
const TASK_ROLES = GRC_ACCESS_ROLES.filter(r => r !== "super_admin");

type Plant = { id: string; code: string; name: string };

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  return qc.invalidateQueries({ queryKey: ["management-review"] });
}

// ── Decisione ────────────────────────────────────────────────────────────────

function DecisionRow({ action, locked }: { action: ReviewAction; locked: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");

  const toggle = useMutation({
    mutationFn: () => managementReviewApi.updateAction(action.id, { status: action.status === "aperto" ? "chiuso" : "aperto" }),
    onSuccess: () => invalidate(qc),
    onError: e => setError(reviewErrorMessage(e, t("management_review.actions.save_error"))),
  });
  const remove = useMutation({
    mutationFn: () => managementReviewApi.deleteAction(action.id),
    onSuccess: () => invalidate(qc),
    onError: e => setError(reviewErrorMessage(e, t("management_review.actions.save_error"))),
  });
  const overdue = isOverdue(action.due_date) && action.status === "aperto";

  return (
    <div className={`border rounded p-2.5 flex items-start gap-2 ${action.status === "chiuso" ? "bg-gray-50" : "bg-white"}`}>
      <div className="flex-1 min-w-0">
        <p className={`text-sm whitespace-pre-line ${action.status === "chiuso" ? "line-through text-gray-400" : "text-gray-800"}`}>{action.description}</p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
          <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700">{t(`management_review.decision_type.${action.decision_type}`)}</span>
          {action.owner_name && <span className="text-xs text-gray-500">👤 {action.owner_name}</span>}
          {action.due_date && (
            <span className={`text-xs font-medium ${overdue ? "text-red-600" : "text-gray-500"}`}>
              📅 {fmtDate(action.due_date)}{overdue ? ` — ${t("management_review.actions.overdue")}` : ""}
            </span>
          )}
          {action.task && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              {t("management_review.actions.linked_task")} <StatusBadge status={action.task_status ?? ""} />
            </span>
          )}
          {action.pdca_cycle && (
            <span className="text-xs text-gray-500">
              {t("management_review.actions.linked_pdca")} <span className="font-medium">{(action.pdca_phase ?? "").toUpperCase()}</span>
            </span>
          )}
        </div>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${action.status === "aperto" ? "bg-orange-100 text-orange-700" : "bg-green-100 text-green-700"}`}>
          {action.status === "aperto" ? t("management_review.actions.open") : t("management_review.actions.closed")}
        </span>
        <button
          title={action.status === "aperto" ? t("management_review.actions.mark_closed") : t("management_review.actions.reopen")}
          onClick={() => toggle.mutate()}
          disabled={toggle.isPending}
          className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 disabled:opacity-40"
        >
          {action.status === "aperto" ? "✓" : "↩"}
        </button>
        {!locked && (confirmDelete ? (
          <span className="flex items-center gap-1">
            <button onClick={() => remove.mutate()} disabled={remove.isPending} className="text-xs text-white bg-red-600 hover:bg-red-700 px-1.5 py-0.5 rounded disabled:opacity-50">
              {t("management_review.actions.yes")}
            </button>
            <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-500 hover:underline">{t("management_review.actions.no")}</button>
          </span>
        ) : (
          <button title={t("management_review.actions.delete")} onClick={() => setConfirmDelete(true)} className="w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 text-gray-400 hover:text-red-600">
            🗑
          </button>
        ))}
      </div>
    </div>
  );
}

function DecisionForm({
  review, agendaItem, users, plants, onDone,
}: {
  review: ManagementReview; agendaItem: ReviewAgendaItem | null; users: GrcUser[]; plants: Plant[]; onDone: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const empty = {
    description: "", decision_type: "miglioramento" as DecisionType, owner: "", due_date: "",
    create_task: false, task_role: "compliance_officer", create_pdca: false, pdca_plant: "",
  };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const set = <K extends keyof typeof empty>(k: K, v: (typeof empty)[K]) => setForm(p => ({ ...p, [k]: v }));

  const create = useMutation({
    mutationFn: () => managementReviewApi.createAction({
      review: review.id,
      agenda_item: agendaItem?.id ?? null,
      decision_type: form.decision_type,
      description: form.description,
      owner: form.owner ? Number(form.owner) : null,
      due_date: form.due_date || null,
      create_task: form.create_task,
      task_role: form.create_task ? form.task_role : "",
      create_pdca: form.create_pdca,
      pdca_plant: form.create_pdca && !review.plant ? form.pdca_plant || null : null,
    }),
    onSuccess: () => { invalidate(qc); setForm(empty); onDone(); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.actions.save_error"))),
  });

  const needsDue = form.create_task && !form.due_date;
  const needsSite = form.create_pdca && !review.plant && !form.pdca_plant;

  return (
    <div className="border border-blue-200 rounded p-3 space-y-2 bg-blue-50">
      <textarea
        rows={2}
        value={form.description}
        onChange={e => set("description", e.target.value)}
        placeholder={t("management_review.actions.desc_ph")}
        className="w-full border rounded px-3 py-2 text-sm"
      />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <select value={form.decision_type} onChange={e => set("decision_type", e.target.value as DecisionType)} className="border rounded px-2 py-1.5 text-sm">
          {DECISION_TYPES.map(dt => <option key={dt} value={dt}>{t(`management_review.decision_type.${dt}`)}</option>)}
        </select>
        <select value={form.owner} onChange={e => set("owner", e.target.value)} className="border rounded px-2 py-1.5 text-sm">
          <option value="">{t("management_review.actions.owner_ph")}</option>
          {users.map(u => <option key={u.id} value={u.id}>{userLabel(u)}</option>)}
        </select>
        <input type="date" value={form.due_date} onChange={e => set("due_date", e.target.value)} className="border rounded px-2 py-1.5 text-sm" />
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={form.create_task} onChange={e => set("create_task", e.target.checked)} />
          {t("management_review.actions.create_task")}
        </label>
        {form.create_task && (
          <select value={form.task_role} onChange={e => set("task_role", e.target.value)} className="border rounded px-2 py-1 text-sm">
            {TASK_ROLES.map(r => <option key={r} value={r}>{t(`governance.roles.${r}`, r)}</option>)}
          </select>
        )}
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={form.create_pdca} onChange={e => set("create_pdca", e.target.checked)} />
          {t("management_review.actions.create_pdca")}
        </label>
        {form.create_pdca && !review.plant && (
          <select value={form.pdca_plant} onChange={e => set("pdca_plant", e.target.value)} className="border rounded px-2 py-1 text-sm">
            <option value="">{t("management_review.actions.pdca_site_ph")}</option>
            {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
          </select>
        )}
      </div>
      {form.create_task && <p className="text-xs text-gray-500">{t("management_review.actions.task_role_hint")}</p>}
      {needsDue && <p className="text-xs text-amber-600">{t("management_review.actions.task_needs_due")}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={() => create.mutate()}
          disabled={create.isPending || !form.description.trim() || needsDue || needsSite}
          className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50"
        >
          {create.isPending ? t("management_review.actions.saving") : t("management_review.actions.add_btn")}
        </button>
        <button onClick={onDone} className="px-3 py-1 border rounded text-xs text-gray-600 hover:bg-white">{t("management_review.actions.cancel")}</button>
      </div>
    </div>
  );
}

// ── Punto all'ordine del giorno ──────────────────────────────────────────────

function AgendaItemCard({
  review, item, decisions, users, plants, snap, locked, highlight,
}: {
  review: ManagementReview; item: ReviewAgendaItem; decisions: ReviewAction[]; users: GrcUser[]; plants: Plant[];
  snap: Snap | null; locked: boolean; highlight: boolean;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  // null = apertura automatica (aperto se il punto è evidenziato come mancante)
  const [openState, setOpen] = useState<boolean | null>(null);
  const open = openState ?? highlight;
  // null = nessuna modifica in corso: si mostra il testo salvato
  const [edited, setEdited] = useState<string | null>(null);
  const discussion = edited ?? item.discussion;
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);


  const save = useMutation({
    mutationFn: () => managementReviewApi.updateAgendaItem(item.id, { discussion }),
    onSuccess: () => { invalidate(qc); setError(""); setEdited(null); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.agenda.save_error"))),
  });
  const remove = useMutation({
    mutationFn: () => managementReviewApi.deleteAgendaItem(item.id),
    onSuccess: () => invalidate(qc),
    onError: e => setError(reviewErrorMessage(e, t("management_review.agenda.save_error"))),
  });

  const clause = ISO_CLAUSE[item.code];
  const title = item.code === "custom" ? item.title : t(`management_review.agenda.items.${item.code}`);
  const covered = item.discussion.trim().length > 0 || decisions.length > 0;
  const dirty = discussion !== item.discussion;

  return (
    <div className={`border rounded ${highlight && !covered ? "border-red-300" : "border-gray-200"}`}>
      <button onClick={() => setOpen(!open)} className="w-full text-left px-3 py-2 flex items-start gap-2 hover:bg-gray-50">
        <span className="text-xs font-bold text-primary-700 w-4 shrink-0 mt-0.5">{clause ?? "•"}</span>
        <span className="flex-1 text-sm text-gray-800">{title}</span>
        <span className="flex items-center gap-1.5 shrink-0">
          {decisions.length > 0 && (
            <span className="text-xs text-gray-500">{t("management_review.agenda.decisions_count", { count: decisions.length })}</span>
          )}
          {item.mandatory && (
            covered
              ? <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">✓</span>
              : <span className={`text-xs px-1.5 py-0.5 rounded ${highlight ? "bg-red-100 text-red-700" : "bg-amber-50 text-amber-700"}`}>{t("management_review.agenda.to_cover")}</span>
          )}
          <span className="text-gray-400 text-xs">{open ? "▲" : "▼"}</span>
        </span>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 space-y-3 border-t border-gray-100">
          {AGENDA_CODES_WITH_DATA.has(item.code) && (
            snap
              ? <div className="bg-gray-50/60 rounded p-2"><AgendaData code={item.code} snap={snap} /></div>
              : <p className="text-xs text-gray-400 italic">{t("management_review.agenda.data_after_snapshot")}</p>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("management_review.agenda.discussion")}</label>
            {locked ? (
              <p className="text-sm text-gray-700 whitespace-pre-line">{item.discussion || <span className="text-gray-400">—</span>}</p>
            ) : (
              <>
                <textarea
                  rows={3}
                  value={discussion}
                  onChange={e => setEdited(e.target.value)}
                  placeholder={t(`management_review.agenda.hints.${item.code}`, t("management_review.agenda.discussion_ph"))}
                  className="w-full border rounded px-3 py-2 text-sm"
                />
                {dirty && (
                  <div className="flex gap-2 mt-1">
                    <button onClick={() => save.mutate()} disabled={save.isPending} className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50">
                      {save.isPending ? t("management_review.agenda.saving") : t("management_review.agenda.save")}
                    </button>
                    <button onClick={() => setEdited(null)} className="px-3 py-1 border rounded text-xs text-gray-600">{t("management_review.agenda.cancel")}</button>
                  </div>
                )}
              </>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-600">{t("management_review.agenda.decisions")}</span>
              {!locked && !adding && (
                <button onClick={() => setAdding(true)} className="text-xs px-2 py-0.5 border border-gray-300 rounded hover:bg-gray-50 text-gray-600">
                  + {t("management_review.actions.add")}
                </button>
              )}
            </div>
            <div className="space-y-2">
              {adding && <DecisionForm review={review} agendaItem={item} users={users} plants={plants} onDone={() => setAdding(false)} />}
              {decisions.map(a => <DecisionRow key={a.id} action={a} locked={locked} />)}
              {decisions.length === 0 && !adding && <p className="text-xs text-gray-400 italic">{t("management_review.actions.none")}</p>}
            </div>
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}
          {!locked && !item.mandatory && (
            <div className="text-right">
              {confirmDelete ? (
                <span className="inline-flex items-center gap-2 text-xs">
                  {t("management_review.agenda.delete_confirm")}
                  <button onClick={() => remove.mutate()} className="text-white bg-red-600 px-2 py-0.5 rounded">{t("management_review.actions.yes")}</button>
                  <button onClick={() => setConfirmDelete(false)} className="text-gray-500 hover:underline">{t("management_review.actions.no")}</button>
                </span>
              ) : (
                <button onClick={() => setConfirmDelete(true)} className="text-xs text-red-500 hover:underline">{t("management_review.agenda.delete_item")}</button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sezione ──────────────────────────────────────────────────────────────────

export function AgendaSection({
  review, users, plants, snap, locked, missing,
}: {
  review: ManagementReview; users: GrcUser[]; plants: Plant[]; snap: Snap | null; locked: boolean; missing: string[];
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [newTitle, setNewTitle] = useState("");
  const [addingLoose, setAddingLoose] = useState(false);
  const [error, setError] = useState("");

  const addItem = useMutation({
    mutationFn: () => managementReviewApi.addAgendaItem(review.id, newTitle),
    onSuccess: () => { invalidate(qc); setNewTitle(""); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.agenda.save_error"))),
  });

  const items = [...(review.agenda_items ?? [])].sort((a, b) => a.order - b.order);
  const actions = review.actions ?? [];
  const loose = actions.filter(a => !a.agenda_item);
  const mandatory = items.filter(i => i.mandatory);
  const covered = mandatory.filter(i => i.discussion.trim() || actions.some(a => a.agenda_item === i.id)).length;

  return (
    <section>
      <div className="flex items-center justify-between mb-1">
        <h4 className="text-sm font-semibold text-gray-700">{t("management_review.agenda.heading")}</h4>
        {mandatory.length > 0 && (
          <span className={`text-xs ${covered === mandatory.length ? "text-green-700" : "text-gray-500"}`}>
            {t("management_review.agenda.progress", { covered, total: mandatory.length })}
          </span>
        )}
      </div>
      <p className="text-xs text-gray-400 mb-2">{t("management_review.agenda.intro")}</p>

      <div className="space-y-2">
        {items.map(item => (
          <AgendaItemCard
            key={item.id}
            review={review}
            item={item}
            decisions={actions.filter(a => a.agenda_item === item.id)}
            users={users}
            plants={plants}
            snap={snap}
            locked={locked}
            highlight={missing.includes(item.code)}
          />
        ))}
      </div>

      {!locked && (
        <div className="flex gap-2 mt-2">
          <input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder={t("management_review.agenda.add_item_ph")}
            className="flex-1 border rounded px-3 py-1.5 text-sm"
          />
          <button
            onClick={() => addItem.mutate()}
            disabled={addItem.isPending || !newTitle.trim()}
            className="px-3 py-1.5 border border-gray-300 rounded text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            + {t("management_review.agenda.add_item")}
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}

      {(loose.length > 0 || (items.length === 0 && !locked)) && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-600">{t("management_review.agenda.other_decisions")}</span>
            {!locked && !addingLoose && items.length === 0 && (
              <button onClick={() => setAddingLoose(true)} className="text-xs px-2 py-0.5 border border-gray-300 rounded hover:bg-gray-50 text-gray-600">
                + {t("management_review.actions.add")}
              </button>
            )}
          </div>
          <div className="space-y-2">
            {addingLoose && <DecisionForm review={review} agendaItem={null} users={users} plants={plants} onDone={() => setAddingLoose(false)} />}
            {loose.map(a => <DecisionRow key={a.id} action={a} locked={locked} />)}
          </div>
        </div>
      )}
    </section>
  );
}
