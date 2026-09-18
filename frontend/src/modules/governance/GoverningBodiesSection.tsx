import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  governanceApi,
  type CommitteeMember,
  type CommitteeType,
  type MemberRole,
  type SecurityCommittee,
} from "../../api/endpoints/governance";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { todayISO } from "../../utils/dates";

// Organi di governo (CdA, comitato sicurezza, direzione): anagrafica di chi
// tiene e approva il riesame di direzione. I componenti si compilano a mano,
// con o senza account: chi siede in CdA di norma non usa la piattaforma.

const WRITE_ROLES = ["super_admin", "compliance_officer"];
const TYPES: CommitteeType[] = ["cda", "comitato", "direzione"];
const MEMBER_ROLES: MemberRole[] = ["presidente", "membro", "segretario"];

type UserOption = { id: number; label: string };

/** Primo messaggio leggibile da un errore DRF (`detail` o errori di campo). */
function apiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: unknown } })?.response?.data;
  if (!data || typeof data !== "object") return fallback;
  const d = data as Record<string, unknown>;
  if (typeof d.detail === "string") return d.detail;
  for (const v of Object.values(d)) {
    if (Array.isArray(v) && typeof v[0] === "string") return v[0];
    if (typeof v === "string") return v;
  }
  return fallback;
}

const input = "w-full border rounded px-3 py-2 text-sm";
const label = "block text-sm font-medium text-gray-700 mb-1";

function Modal({ title, children, error, onClose, onSave, saving, canSave }: {
  title: string; children: React.ReactNode; error: string; onClose: () => void;
  onSave: () => void; saving: boolean; canSave: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="space-y-3">{children}</div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button onClick={onSave} disabled={saving || !canSave}
                  className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {saving ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

function BodyModal({ body, onClose }: { body?: SecurityCommittee; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });
  const [form, setForm] = useState({
    name: body?.name ?? "",
    committee_type: body?.committee_type ?? ("cda" as CommitteeType),
    description: body?.description ?? "",
    plants: body?.plants ?? ([] as string[]),
  });
  const [wholeOrg, setWholeOrg] = useState(!body || body.plants.length === 0);
  const [error, setError] = useState("");

  const save = useMutation({
    mutationFn: () => {
      const payload = { ...form, plants: wholeOrg ? [] : form.plants };
      return body ? governanceApi.updateCommittee(body.id, payload) : governanceApi.createCommittee(payload);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["committees"] }); onClose(); },
    onError: e => setError(apiError(e, t("common.error"))),
  });

  const togglePlant = (id: string) =>
    setForm(f => ({ ...f, plants: f.plants.includes(id) ? f.plants.filter(p => p !== id) : [...f.plants, id] }));

  return (
    <Modal
      title={body ? t("governance.bodies.edit_title") : t("governance.bodies.new_title")}
      error={error} onClose={onClose} onSave={() => save.mutate()} saving={save.isPending}
      canSave={!!form.name.trim() && (wholeOrg || form.plants.length > 0)}
    >
      <div>
        <label className={label}>{t("governance.bodies.fields.name")} *</label>
        <input className={input} value={form.name} placeholder={t("governance.bodies.placeholders.name")}
               onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
      </div>
      <div>
        <label className={label}>{t("governance.bodies.fields.type")}</label>
        <select className={input} value={form.committee_type}
                onChange={e => setForm(f => ({ ...f, committee_type: e.target.value as CommitteeType }))}>
          {TYPES.map(k => <option key={k} value={k}>{t(`governance.bodies.types.${k}`)}</option>)}
        </select>
        {form.committee_type === "cda" && (
          <p className="text-xs text-gray-500 mt-1">{t("governance.bodies.cda_hint")}</p>
        )}
      </div>
      <div>
        <label className={label}>{t("governance.bodies.fields.scope")}</label>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={wholeOrg} onChange={e => setWholeOrg(e.target.checked)} />
          {t("governance.bodies.whole_org")}
        </label>
        {!wholeOrg && (
          <div className="border rounded mt-2 max-h-40 overflow-y-auto divide-y divide-gray-100">
            {plants.map(p => (
              <label key={p.id} className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" checked={form.plants.includes(p.id)} onChange={() => togglePlant(p.id)} />
                <span>[{p.code}] {p.name}</span>
              </label>
            ))}
          </div>
        )}
        <p className="text-xs text-gray-500 mt-1">{t("governance.bodies.scope_hint")}</p>
      </div>
      <div>
        <label className={label}>{t("governance.bodies.fields.description")}</label>
        <textarea className={input} rows={2} value={form.description}
                  placeholder={t("governance.bodies.placeholders.description")}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
      </div>
    </Modal>
  );
}

function MemberModal({ body, member, users, onClose }: {
  body: SecurityCommittee; member?: CommitteeMember; users: UserOption[]; onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    full_name: member?.full_name ?? "",
    position: member?.position ?? "",
    body_role: member?.body_role ?? ("membro" as MemberRole),
    user: member?.user ?? (null as number | null),
    valid_from: member?.valid_from ?? todayISO(),
    valid_until: member?.valid_until ?? "",
  });
  const [error, setError] = useState("");

  const save = useMutation({
    mutationFn: () => {
      const payload = { ...form, valid_until: form.valid_until || null };
      return member
        ? governanceApi.updateMember(member.id, payload)
        : governanceApi.createMember({ ...payload, committee: body.id });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["committees"] }); onClose(); },
    onError: e => setError(apiError(e, t("common.error"))),
  });

  return (
    <Modal
      title={member ? t("governance.bodies.member_edit_title") : t("governance.bodies.member_new_title", { body: body.name })}
      error={error} onClose={onClose} onSave={() => save.mutate()} saving={save.isPending}
      canSave={!!form.full_name.trim() && !!form.valid_from}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className={label}>{t("governance.bodies.fields.full_name")} *</label>
          <input className={input} value={form.full_name}
                 onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
        </div>
        <div>
          <label className={label}>{t("governance.bodies.fields.position")}</label>
          <input className={input} value={form.position} placeholder={t("governance.bodies.placeholders.position")}
                 onChange={e => setForm(f => ({ ...f, position: e.target.value }))} />
        </div>
      </div>
      <div>
        <label className={label}>{t("governance.bodies.fields.body_role")}</label>
        <select className={input} value={form.body_role}
                onChange={e => setForm(f => ({ ...f, body_role: e.target.value as MemberRole }))}>
          {MEMBER_ROLES.map(r => <option key={r} value={r}>{t(`governance.bodies.member_roles.${r}`)}</option>)}
        </select>
      </div>
      <div>
        <label className={label}>{t("governance.bodies.fields.user")}</label>
        <select className={input} value={form.user ?? ""}
                onChange={e => setForm(f => ({ ...f, user: e.target.value ? Number(e.target.value) : null }))}>
          <option value="">{t("governance.bodies.no_account")}</option>
          {users.map(u => <option key={u.id} value={u.id}>{u.label}</option>)}
        </select>
        <p className="text-xs text-gray-500 mt-1">{t("governance.bodies.user_hint")}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={label}>{t("governance.bodies.fields.valid_from")} *</label>
          <input type="date" className={input} value={form.valid_from}
                 onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))} />
        </div>
        <div>
          <label className={label}>{t("governance.bodies.fields.valid_until")}</label>
          <input type="date" className={input} value={form.valid_until}
                 onChange={e => setForm(f => ({ ...f, valid_until: e.target.value }))} />
        </div>
      </div>
    </Modal>
  );
}

function BodyCard({ body, canWrite, onEdit, onAddMember, onEditMember }: {
  body: SecurityCommittee; canWrite: boolean;
  onEdit: () => void; onAddMember: () => void; onEditMember: (m: CommitteeMember) => void;
}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [showFormer, setShowFormer] = useState(false);
  const [error, setError] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: ["committees"] });
  const fmt = (d: string | null) => d ? new Date(`${d}T00:00:00`).toLocaleDateString(i18n.language) : "—";

  const endMember = useMutation({
    mutationFn: (m: CommitteeMember) => governanceApi.updateMember(m.id, { valid_until: todayISO() }),
    onSuccess: () => { refresh(); setError(""); },
    onError: e => setError(apiError(e, t("common.error"))),
  });
  const deleteMember = useMutation({
    mutationFn: (m: CommitteeMember) => governanceApi.deleteMember(m.id),
    onSuccess: () => { refresh(); setError(""); },
    onError: e => setError(apiError(e, t("common.error"))),
  });
  const deleteBody = useMutation({
    mutationFn: () => governanceApi.deleteCommittee(body.id),
    onSuccess: refresh,
    onError: e => setError(apiError(e, t("common.error"))),
  });

  const active = body.members.filter(m => m.is_active);
  const former = body.members.filter(m => !m.is_active);
  const hasChair = active.some(m => m.body_role === "presidente");

  const rows = (list: CommitteeMember[], muted: boolean) => list.map(m => (
    <tr key={m.id} className={`border-b border-gray-100 ${muted ? "text-gray-400" : ""}`}>
      <td className="px-3 py-2">
        <span className={muted ? "" : "font-medium text-gray-800"}>{m.full_name}</span>
        {m.position && <p className="text-xs text-gray-500">{m.position}</p>}
      </td>
      <td className="px-3 py-2 whitespace-nowrap">{t(`governance.bodies.member_roles.${m.body_role}`)}</td>
      <td className="px-3 py-2 whitespace-nowrap text-xs">
        {m.user ? (
          <span className={m.user_is_active === false ? "text-red-600" : "text-gray-700"}>
            {m.user_name}{m.user_is_active === false && ` · ${t("governance.bodies.account_inactive")}`}
          </span>
        ) : <span className="text-gray-400">—</span>}
      </td>
      <td className="px-3 py-2 whitespace-nowrap text-xs">{fmt(m.valid_from)} → {m.valid_until ? fmt(m.valid_until) : t("governance.bodies.ongoing")}</td>
      {canWrite && (
        <td className="px-3 py-2 whitespace-nowrap text-right text-xs space-x-2">
          <button className="text-primary-600 hover:underline" onClick={() => onEditMember(m)}>{t("actions.edit")}</button>
          {!muted && (
            <button className="text-amber-700 hover:underline"
                    onClick={() => window.confirm(t("governance.bodies.end_confirm", { name: m.full_name })) && endMember.mutate(m)}>
              {t("governance.bodies.end_term")}
            </button>
          )}
          <button className="text-red-600 hover:underline"
                  onClick={() => window.confirm(t("governance.bodies.delete_member_confirm", { name: m.full_name })) && deleteMember.mutate(m)}>
            {t("actions.delete")}
          </button>
        </td>
      )}
    </tr>
  ));

  return (
    <div className="border border-gray-200 rounded-lg p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-gray-900">{body.name}</span>
            <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
              {t(`governance.bodies.types.${body.committee_type}`)}
            </span>
            {body.is_management_body && (
              <span className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded">
                {t("governance.bodies.nis2_badge")}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {body.plant_codes.length ? body.plant_codes.join(", ") : t("governance.bodies.whole_org")}
          </p>
          {body.description && <p className="text-xs text-gray-600 mt-1">{body.description}</p>}
        </div>
        {canWrite && (
          <div className="flex gap-2 text-xs">
            <button className="px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700" onClick={onAddMember}>
              {t("governance.bodies.add_member")}
            </button>
            <button className="px-2 py-1 border rounded hover:bg-gray-50" onClick={onEdit}>{t("actions.edit")}</button>
            <button className="px-2 py-1 border border-red-200 text-red-600 rounded hover:bg-red-50"
                    onClick={() => window.confirm(t("governance.bodies.delete_confirm", { name: body.name })) && deleteBody.mutate()}>
              {t("actions.delete")}
            </button>
          </div>
        )}
      </div>

      {active.length > 0 && !hasChair && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-2">
          {t("governance.bodies.no_chair")}
        </p>
      )}
      {error && <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1 mt-2">{error}</p>}

      {active.length === 0 ? (
        <p className="text-sm text-gray-400 italic mt-2">{t("governance.bodies.no_members")}</p>
      ) : (
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-500 uppercase tracking-wide border-b border-gray-200">
              <tr>
                <th className="px-3 py-1.5 text-left font-medium">{t("governance.bodies.fields.full_name")}</th>
                <th className="px-3 py-1.5 text-left font-medium">{t("governance.bodies.fields.body_role")}</th>
                <th className="px-3 py-1.5 text-left font-medium">{t("governance.bodies.fields.user")}</th>
                <th className="px-3 py-1.5 text-left font-medium">{t("governance.bodies.fields.term")}</th>
                {canWrite && <th />}
              </tr>
            </thead>
            <tbody>
              {rows(active, false)}
              {showFormer && rows(former, true)}
            </tbody>
          </table>
        </div>
      )}
      {former.length > 0 && (
        <button className="text-xs text-gray-500 hover:text-gray-700 mt-2" onClick={() => setShowFormer(s => !s)}>
          {showFormer ? t("governance.bodies.hide_former") : t("governance.bodies.show_former", { n: former.length })}
        </button>
      )}
    </div>
  );
}

export function GoverningBodiesSection({ users }: { users: UserOption[] }) {
  const { t } = useTranslation();
  const role = useAuthStore(s => s.user?.role) ?? "";
  const canWrite = WRITE_ROLES.includes(role);
  const [bodyModal, setBodyModal] = useState<{ body?: SecurityCommittee } | null>(null);
  const [memberModal, setMemberModal] = useState<{ body: SecurityCommittee; member?: CommitteeMember } | null>(null);

  const { data: bodies = [], isLoading } = useQuery({
    queryKey: ["committees"],
    queryFn: () => governanceApi.committees(),
    retry: false,
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
        <h3 className="text-sm font-semibold text-gray-700">{t("governance.sections.committees")}</h3>
        {canWrite && (
          <button onClick={() => setBodyModal({})}
                  className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
            {t("governance.bodies.new_open")}
          </button>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-3">{t("governance.bodies.intro")}</p>

      {isLoading ? (
        <p className="text-sm text-gray-400">{t("common.loading")}</p>
      ) : bodies.length === 0 ? (
        <p className="text-sm text-gray-400 italic">{t("governance.empty.committees")}</p>
      ) : (
        <div className="space-y-3">
          {bodies.map(b => (
            <BodyCard
              key={b.id} body={b} canWrite={canWrite}
              onEdit={() => setBodyModal({ body: b })}
              onAddMember={() => setMemberModal({ body: b })}
              onEditMember={m => setMemberModal({ body: b, member: m })}
            />
          ))}
        </div>
      )}

      {bodyModal && <BodyModal body={bodyModal.body} onClose={() => setBodyModal(null)} />}
      {memberModal && (
        <MemberModal body={memberModal.body} member={memberModal.member} users={users}
                     onClose={() => setMemberModal(null)} />
      )}
    </div>
  );
}
