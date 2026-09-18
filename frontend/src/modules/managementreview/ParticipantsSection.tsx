import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { governanceApi, type SecurityCommittee } from "../../api/endpoints/governance";
import {
  managementReviewApi,
  reviewErrorMessage,
  type Attendance,
  type ManagementReview,
  type ParticipantRole,
  type ReviewParticipant,
} from "../../api/endpoints/managementReview";
import type { GrcUser } from "../../api/endpoints/users";
import { userLabel } from "./shared";

// Convocati del riesame: componenti dell'organo (anche senza account), utenti
// della piattaforma e ospiti. Nome e qualifica si congelano nel verbale.

const ROLES: ParticipantRole[] = ["presidente", "membro", "segretario", "ospite"];
const ATTENDANCE: Attendance[] = ["presente", "assente", "delegato"];

const ATTENDANCE_STYLE: Record<Attendance, string> = {
  presente: "text-green-700",
  assente: "text-gray-400",
  delegato: "text-amber-700",
};

/** Organi selezionabili per il perimetro del riesame: un riesame di sito può
 *  essere tenuto da un organo di organizzazione o da uno che include il sito. */
export function bodiesForScope(bodies: SecurityCommittee[], plantId: string | null) {
  return bodies.filter(b => (plantId ? b.plants.length === 0 || b.plants.includes(plantId) : b.plants.length === 0));
}

function toRow(p: ReviewParticipant): ReviewParticipant {
  return {
    member: p.member, user: p.user, full_name: p.full_name, position: p.position,
    body_role: p.body_role, is_chair: p.is_chair, attendance: p.attendance, delegate_name: p.delegate_name,
  };
}

export function ParticipantsSection({ review, users, locked, canWrite }: {
  review: ManagementReview; users: GrcUser[]; locked: boolean; canWrite: boolean;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [rows, setRows] = useState<ReviewParticipant[]>([]);
  const [guest, setGuest] = useState({ full_name: "", position: "" });
  const [error, setError] = useState("");

  const { data: bodies = [] } = useQuery({
    queryKey: ["committees"],
    queryFn: () => governanceApi.committees(),
    retry: false,
    enabled: canWrite,
  });
  const body = bodies.find(b => b.id === review.governing_body);
  const refresh = () => qc.invalidateQueries({ queryKey: ["management-review"] });

  const save = useMutation({
    mutationFn: () => managementReviewApi.setParticipants(review.id, rows),
    onSuccess: () => { refresh(); setEditing(false); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.participants.save_error"))),
  });
  const fromBody = useMutation({
    mutationFn: () => managementReviewApi.participantsFromBody(review.id),
    onSuccess: () => { refresh(); setEditing(false); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.participants.save_error"))),
  });
  const changeBody = useMutation({
    mutationFn: (id: string | null) => managementReviewApi.update(review.id, { governing_body: id }),
    onSuccess: () => { refresh(); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.participants.save_error"))),
  });

  const patch = (i: number, p: Partial<ReviewParticipant>) =>
    setRows(rs => rs.map((r, j) => {
      if (p.is_chair && j !== i) return { ...r, is_chair: false };
      return j === i ? { ...r, ...p } : r;
    }));

  const availableMembers = (body?.members ?? []).filter(m => m.is_active && !rows.some(r => r.member === m.id));
  const availableUsers = users.filter(u => u.is_active !== false && !rows.some(r => r.user === u.id));

  function addMember(id: string) {
    const m = body?.members.find(x => x.id === id);
    if (!m) return;
    setRows(rs => [...rs, {
      member: m.id, user: m.user, full_name: m.full_name, position: m.position, body_role: m.body_role,
      is_chair: false, attendance: "presente", delegate_name: "",
    }]);
  }
  function addUser(id: string) {
    const u = users.find(x => String(x.id) === id);
    if (!u) return;
    setRows(rs => [...rs, {
      member: null, user: u.id, full_name: userLabel(u), position: "", body_role: "ospite",
      is_chair: false, attendance: "presente", delegate_name: "",
    }]);
  }
  function addGuest() {
    if (!guest.full_name.trim()) return;
    setRows(rs => [...rs, {
      member: null, user: null, full_name: guest.full_name.trim(), position: guest.position.trim(),
      body_role: "ospite", is_chair: false, attendance: "presente", delegate_name: "",
    }]);
    setGuest({ full_name: "", position: "" });
  }

  const editable = canWrite && !locked;
  const cell = "px-2 py-1.5 align-top";
  const sel = "border rounded px-1.5 py-1 text-xs";

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h4 className="text-sm font-semibold text-gray-700">{t("management_review.participants.heading")}</h4>
        {editable && !editing && (
          <div className="flex gap-2">
            {review.governing_body && (
              <button
                onClick={() => window.confirm(t("management_review.participants.from_body_confirm")) && fromBody.mutate()}
                disabled={fromBody.isPending}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 text-gray-600 disabled:opacity-50">
                {t("management_review.participants.from_body")}
              </button>
            )}
            <button onClick={() => { setRows(review.participants.map(toRow)); setEditing(true); }}
                    className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 text-gray-600">
              {t("management_review.participants.edit")}
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm mb-2">
        <span className="text-gray-500">{t("management_review.participants.body")}:</span>
        {editable && !editing ? (
          <select value={review.governing_body ?? ""} className="border rounded px-2 py-1 text-sm"
                  onChange={e => changeBody.mutate(e.target.value || null)}>
            <option value="">{t("management_review.participants.no_body")}</option>
            {bodiesForScope(bodies, review.plant).map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        ) : (
          <span className="text-gray-800 font-medium">{review.governing_body_name ?? "—"}</span>
        )}
      </div>

      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      {editing ? (
        <div className="border border-blue-200 rounded p-3 bg-blue-50 space-y-3">
          <div className="overflow-x-auto bg-white rounded border border-gray-200">
            <table className="w-full text-xs">
              <thead className="text-gray-500 border-b border-gray-200">
                <tr>
                  <th className={`${cell} text-left font-medium`}>{t("management_review.participants.col_name")}</th>
                  <th className={`${cell} text-left font-medium`}>{t("management_review.participants.col_role")}</th>
                  <th className={`${cell} text-left font-medium`}>{t("management_review.participants.col_attendance")}</th>
                  <th className={`${cell} text-center font-medium`}>{t("management_review.participants.chair")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.member ?? r.user ?? r.full_name}-${i}`} className="border-b border-gray-100">
                    <td className={cell}>
                      <p className="font-medium text-gray-800">{r.full_name}</p>
                      <input value={r.position} placeholder={t("management_review.participants.position_ph")}
                             onChange={e => patch(i, { position: e.target.value })}
                             className="border rounded px-1.5 py-0.5 text-xs w-full mt-0.5" />
                    </td>
                    <td className={cell}>
                      <select className={sel} value={r.body_role} onChange={e => patch(i, { body_role: e.target.value as ParticipantRole })}>
                        {ROLES.map(k => <option key={k} value={k}>{t(`management_review.participants.roles.${k}`)}</option>)}
                      </select>
                    </td>
                    <td className={cell}>
                      <select className={sel} value={r.attendance} onChange={e => patch(i, { attendance: e.target.value as Attendance })}>
                        {ATTENDANCE.map(k => <option key={k} value={k}>{t(`management_review.participants.attendance.${k}`)}</option>)}
                      </select>
                      {r.attendance === "delegato" && (
                        <input value={r.delegate_name} placeholder={t("management_review.participants.delegate_ph")}
                               onChange={e => patch(i, { delegate_name: e.target.value })}
                               className="border rounded px-1.5 py-0.5 text-xs w-full mt-1" />
                      )}
                    </td>
                    <td className={`${cell} text-center`}>
                      <input type="radio" name="chair" checked={r.is_chair} onChange={() => patch(i, { is_chair: true })} />
                    </td>
                    <td className={`${cell} text-right`}>
                      <button className="text-red-600 hover:underline" onClick={() => setRows(rs => rs.filter((_, j) => j !== i))}>
                        {t("actions.delete")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
            {body && (
              <select className="border rounded px-2 py-1.5" value="" onChange={e => addMember(e.target.value)}
                      disabled={availableMembers.length === 0}>
                <option value="">{t("management_review.participants.add_member")}</option>
                {availableMembers.map(m => <option key={m.id} value={m.id}>{m.full_name}{m.position ? ` — ${m.position}` : ""}</option>)}
              </select>
            )}
            <select className="border rounded px-2 py-1.5" value="" onChange={e => addUser(e.target.value)}>
              <option value="">{t("management_review.participants.add_user")}</option>
              {availableUsers.map(u => <option key={u.id} value={u.id}>{userLabel(u)}</option>)}
            </select>
            <div className="flex gap-1">
              <input className="border rounded px-2 py-1.5 flex-1 min-w-0" value={guest.full_name}
                     placeholder={t("management_review.participants.guest_name_ph")}
                     onChange={e => setGuest(g => ({ ...g, full_name: e.target.value }))} />
              <input className="border rounded px-2 py-1.5 flex-1 min-w-0" value={guest.position}
                     placeholder={t("management_review.participants.position_ph")}
                     onChange={e => setGuest(g => ({ ...g, position: e.target.value }))} />
              <button className="px-2 border rounded bg-white hover:bg-gray-50" onClick={addGuest}
                      disabled={!guest.full_name.trim()}>+</button>
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={() => save.mutate()} disabled={save.isPending}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50">
              {save.isPending ? t("management_review.participants.saving") : t("management_review.participants.save")}
            </button>
            <button onClick={() => { setEditing(false); setError(""); }}
                    className="px-3 py-1 border rounded text-xs text-gray-600 hover:bg-white">
              {t("management_review.participants.cancel")}
            </button>
          </div>
        </div>
      ) : review.participants.length === 0 ? (
        <p className="text-sm text-amber-600">{t("management_review.participants.none_yet")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>
              {review.participants.map(p => (
                <tr key={p.id} className="border-b border-gray-100">
                  <td className="py-1.5 pr-3">
                    <span className="font-medium text-gray-800">{p.full_name}</span>
                    {p.is_chair && (
                      <span className="ml-2 text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded">
                        {t("management_review.participants.chair")}
                      </span>
                    )}
                    {p.position && <p className="text-xs text-gray-500">{p.position}</p>}
                  </td>
                  <td className="py-1.5 pr-3 text-xs text-gray-600 whitespace-nowrap">
                    {t(`management_review.participants.roles.${p.body_role}`)}
                  </td>
                  <td className={`py-1.5 text-xs whitespace-nowrap ${ATTENDANCE_STYLE[p.attendance]}`}>
                    {t(`management_review.participants.attendance.${p.attendance}`)}
                    {p.attendance === "delegato" && p.delegate_name && `: ${p.delegate_name}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
