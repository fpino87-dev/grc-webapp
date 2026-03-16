import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { governanceApi, type RoleAssignment, type SecurityCommittee } from "../../api/endpoints/governance";
import { usersApi } from "../../api/endpoints/users";
import { plantsApi } from "../../api/endpoints/plants";
import { apiClient } from "../../api/client";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

const ROLE_LABELS: Record<string, string> = {
  ciso:                   "CISO",
  compliance_officer:     "Compliance Officer",
  risk_manager:           "Risk Manager",
  internal_auditor:       "Auditor Interno",
  external_auditor:       "Auditor Esterno",
  plant_manager:          "Plant Manager",
  control_owner:          "Control Owner",
  plant_security_officer: "Plant Security Officer",
  nis2_contact:           "Contatto NIS2",
  dpo:                    "DPO",
  isms_manager:           "ISMS Manager",
  comitato_membro:        "Membro Comitato",
  bu_referente:           "Referente BU",
  raci_responsible:       "RACI Responsible",
  raci_accountable:       "RACI Accountable",
};

const TODAY = new Date().toISOString().slice(0, 10);

// ── Helpers ───────────────────────────────────────────────────────────────────

function scopeBadge(a: RoleAssignment) {
  if (a.scope_label) {
    const colors: Record<string, string> = {
      Globale: "bg-blue-50 text-blue-700 border-blue-200",
    };
    const isGlobal = a.scope_type === "org";
    const isBu = a.scope_type === "bu";
    const cls = isGlobal
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : isBu
      ? "bg-indigo-50 text-indigo-700 border-indigo-200"
      : "bg-green-50 text-green-700 border-green-200";
    return (
      <span className={`text-xs px-1.5 py-0.5 rounded border ${cls}`}>
        {a.scope_label}
      </span>
    );
  }
  return null;
}

function roleBadge(a: RoleAssignment) {
  if (!a.valid_until) {
    return <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Attivo</span>;
  }
  const days = Math.ceil((new Date(a.valid_until).getTime() - Date.now()) / 86400000);
  if (days < 0) {
    return <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Scaduto</span>;
  }
  if (days <= 30) {
    return <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Scade in {days}gg</span>;
  }
  return <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Attivo</span>;
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ msg, onClose }: { msg: string; onClose: () => void }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 bg-green-600 text-white px-5 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-sm">
      <span className="text-sm">{msg}</span>
      <button onClick={onClose} className="text-white/80 hover:text-white text-lg leading-none">×</button>
    </div>
  );
}

// ── Modal: Nuova assegnazione ─────────────────────────────────────────────────

function RoleAssignmentModal({
  users,
  onClose,
}: { users: { id: number; email: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, any>>({
    scope_type: "org",
    valid_from: TODAY,
  });
  const [error, setError] = useState("");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const { data: busData } = useQuery({
    queryKey: ["business-units"],
    queryFn: async () => {
      const res = await apiClient.get("/plants/business-units/");
      const d = res.data;
      return Array.isArray(d) ? d : (d?.results ?? []);
    },
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => governanceApi.createRoleAssignment(form as any),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["role-assignments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const val = e.target.value || null;
    if (e.target.name === "scope_type") {
      setForm(prev => ({ ...prev, scope_type: val, scope_id: null }));
    } else {
      setForm(prev => ({ ...prev, [e.target.name]: val }));
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Nuova assegnazione ruolo</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Utente *</label>
            <select name="user" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— seleziona —</option>
              {users.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ruolo *</label>
            <select name="role" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— seleziona —</option>
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ambito</label>
            <select name="scope_type" defaultValue="org" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="org">Globale — tutta l&apos;organizzazione</option>
              <option value="bu">Business Unit specifica</option>
              <option value="plant">Sito specifico</option>
            </select>
          </div>
          {form.scope_type === "bu" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Unit *</label>
              <select name="scope_id" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona BU —</option>
                {(busData ?? []).map((b: any) => (
                  <option key={b.id} value={b.id}>{b.code} — {b.name}</option>
                ))}
              </select>
            </div>
          )}
          {form.scope_type === "plant" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
              <select name="scope_id" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona sito —</option>
                {(plants ?? []).map((p) => (
                  <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valido dal *</label>
              <input type="date" name="valid_from" defaultValue={TODAY} onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valido fino al</label>
              <input type="date" name="valid_until" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={
              mutation.isPending || !form.user || !form.role || !form.valid_from ||
              (form.scope_type !== "org" && !form.scope_id)
            }
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Assegna ruolo"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Termina ruolo ──────────────────────────────────────────────────────

function TerminaModal({
  assignment,
  onClose,
  onSuccess,
}: { assignment: RoleAssignment; onClose: () => void; onSuccess: (msg: string) => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(TODAY);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => governanceApi.terminaRole(assignment.id, { reason, termination_date: date }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      onSuccess(data.message);
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || "Errore durante la terminazione."),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-semibold">Termina ruolo</h3>
        <p className="text-sm text-gray-600">
          Stai per terminare il ruolo{" "}
          <strong>{ROLE_LABELS[assignment.role] ?? assignment.role}</strong>{" "}
          di <strong>{assignment.user_name ?? assignment.user_email}</strong>.
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Data fine</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Motivo *</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={3}
            placeholder="min 5 caratteri..."
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || reason.trim().length < 5}
            className="px-4 py-2 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Terminazione..." : "Conferma terminazione"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Sostituisci ruolo ──────────────────────────────────────────────────

function SostituisciModal({
  assignment,
  users,
  onClose,
  onSuccess,
}: {
  assignment: RoleAssignment;
  users: { id: number; email: string; name: string }[];
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const qc = useQueryClient();
  const [newUserId, setNewUserId] = useState<number | "">("");
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(TODAY);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      governanceApi.sostituisciRole(assignment.id, {
        new_user_id: newUserId as number,
        reason,
        handover_date: date,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      onSuccess(data.message);
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || "Errore durante la successione."),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-semibold">Successione ruolo</h3>
        <p className="text-sm text-gray-600">
          Ruolo: <strong>{ROLE_LABELS[assignment.role] ?? assignment.role}</strong>
          {" "}— titolare attuale: <strong>{assignment.user_name ?? assignment.user_email}</strong>
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nuovo titolare *</label>
          <select
            value={newUserId}
            onChange={e => setNewUserId(Number(e.target.value))}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">— seleziona —</option>
            {users.filter(u => u.id !== assignment.user).map(u => (
              <option key={u.id} value={u.id}>{u.name || u.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Data passaggio</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Motivo / note</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
            placeholder="Opzionale..."
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !newUserId}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Successione..." : "Conferma successione"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Comitato ───────────────────────────────────────────────────────────

function CommitteeModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<SecurityCommittee>>({ committee_type: "centrale", frequency: "trimestrale" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: governanceApi.createCommittee,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["committees"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || "Errore"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value || null }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo comitato</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input name="name" onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder="es. Comitato per la Sicurezza" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select name="committee_type" defaultValue="centrale" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="centrale">Centrale</option>
                <option value="bu">BU</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequenza</label>
              <select name="frequency" defaultValue="trimestrale" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="mensile">Mensile</option>
                <option value="trimestrale">Trimestrale</option>
                <option value="semestrale">Semestrale</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prossima riunione</label>
            <input type="datetime-local" name="next_meeting_at" onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea comitato"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function GovernancePage() {
  const [showRoleModal, setShowRoleModal]         = useState(false);
  const [showCommitteeModal, setShowCommitteeModal] = useState(false);
  const [terminaTarget, setTerminaTarget]         = useState<RoleAssignment | null>(null);
  const [sostituisciTarget, setSostituisciTarget] = useState<RoleAssignment | null>(null);
  const [toast, setToast]                         = useState<string | null>(null);

  const { data: assignments, isLoading: loadingAssign } = useQuery({
    queryKey: ["role-assignments"],
    queryFn: () => governanceApi.roleAssignments(),
    retry: false,
  });

  const { data: committees, isLoading: loadingComm } = useQuery({
    queryKey: ["committees"],
    queryFn: () => governanceApi.committees(),
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const { data: vacanti } = useQuery({
    queryKey: ["governance-vacanti"],
    queryFn: () => governanceApi.vacanti(),
    retry: false,
  });

  const { data: inScadenza } = useQuery({
    queryKey: ["governance-in-scadenza"],
    queryFn: () => governanceApi.inScadenza(30),
    retry: false,
  });

  const userList = (users ?? []).map(u => ({
    id:    u.id,
    email: u.email,
    name:  `${u.first_name} ${u.last_name}`.trim() || u.username || u.email,
  }));

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Governance</h2>
          <p className="text-sm text-gray-500 mt-1">Ruoli normativi, comitati e successione incarichi</p>
        </div>
        <ModuleHelp
          title="Governance — M00"
          description="Gestisce i ruoli normativi (CISO, contatto NIS2, DPO ecc.) con validità temporale. I ruoli scaduti o vacanti generano alert automatici perché impattano la conformità NIS2 e ISO 27001."
          steps={[
            "Assegna un ruolo a un utente con data inizio e fine",
            "Per sostituire un titolare usa 'Sostituisci' — la successione è atomica",
            "Per terminare senza successore usa 'Termina' con motivo",
            "I ruoli obbligatori vacanti (CISO, NIS2, DPO, ISMS) generano alert in cima",
            "Collega il documento di nomina per avere evidenza formale",
          ]}
          connections={[
            { module: "M02 RBAC",              relation: "Ruolo normativo distinto dal ruolo applicativo" },
            { module: "M13 Management Review", relation: "Ruoli vacanti compaiono nello snapshot" },
          ]}
          configNeeded={["Creare prima gli utenti in M02"]}
        />
      </div>

      {/* Alert: ruoli vacanti */}
      {(vacanti?.count ?? 0) > 0 && (
        <div className="border border-red-300 bg-red-50 rounded-lg p-4">
          <p className="font-semibold text-red-700">
            🚨 {vacanti!.count} ruoli obbligatori senza titolare attivo
          </p>
          <ul className="mt-2 text-sm text-red-600 space-y-0.5">
            {vacanti!.vacant_roles.map(r => (
              <li key={r}>• {ROLE_LABELS[r] ?? r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Alert: ruoli in scadenza */}
      {(inScadenza?.expiring?.length ?? 0) > 0 && (
        <div className="border border-amber-300 bg-amber-50 rounded-lg p-4">
          <p className="font-semibold text-amber-700">
            ⚠ {inScadenza!.expiring.length} ruoli in scadenza nei prossimi 30 giorni
          </p>
          <ul className="mt-2 text-sm text-amber-600 space-y-0.5">
            {inScadenza!.expiring.map(r => (
              <li key={r.id}>
                • {ROLE_LABELS[r.role] ?? r.role} — {r.user} (scade il {r.valid_until})
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ruoli normativi */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Ruoli normativi</h3>
            <button
              onClick={() => setShowRoleModal(true)}
              className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
            >
              + Assegna
            </button>
          </div>

          {loadingAssign ? (
            <p className="text-sm text-gray-400">Caricamento...</p>
          ) : !assignments?.length ? (
            <p className="text-sm text-gray-400 italic">Nessun ruolo assegnato</p>
          ) : (
            <div className="space-y-1">
              {assignments.map((a) => (
                <div key={a.id} className="flex items-start justify-between py-2 border-b border-gray-50 last:border-0 gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-800 text-sm">
                        {ROLE_LABELS[a.role] ?? a.role}
                      </span>
                      {roleBadge(a)}
                      {scopeBadge(a)}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {a.user_name ?? a.user_email ?? String(a.user)}
                      {a.valid_until && (
                        <span className="ml-2 text-gray-400">
                          fino al {new Date(a.valid_until).toLocaleDateString("it-IT")}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 flex-shrink-0 mt-0.5">
                    <button
                      onClick={() => setSostituisciTarget(a)}
                      className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 border border-blue-200"
                    >
                      Sostituisci
                    </button>
                    <button
                      onClick={() => setTerminaTarget(a)}
                      className="text-xs px-2 py-1 bg-orange-50 text-orange-700 rounded hover:bg-orange-100 border border-orange-200"
                    >
                      Termina
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Comitati */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Comitati per la sicurezza</h3>
            <button
              onClick={() => setShowCommitteeModal(true)}
              className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
            >
              + Nuovo
            </button>
          </div>
          {loadingComm ? (
            <p className="text-sm text-gray-400">Caricamento...</p>
          ) : !committees?.length ? (
            <p className="text-sm text-gray-400 italic">Nessun comitato configurato</p>
          ) : (
            <div className="space-y-3">
              {committees.map((c) => (
                <div key={c.id} className="border border-gray-100 rounded p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-800 text-sm">{c.name}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {c.committee_type}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Frequenza: {c.frequency}
                    {c.next_meeting_at && (
                      <> — prossima:{" "}
                        <span className="font-medium">
                          {new Date(c.next_meeting_at).toLocaleDateString("it-IT")}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modali */}
      {showRoleModal && (
        <RoleAssignmentModal users={userList} onClose={() => setShowRoleModal(false)} />
      )}
      {showCommitteeModal && (
        <CommitteeModal onClose={() => setShowCommitteeModal(false)} />
      )}
      {terminaTarget && (
        <TerminaModal
          assignment={terminaTarget}
          onClose={() => setTerminaTarget(null)}
          onSuccess={showToast}
        />
      )}
      {sostituisciTarget && (
        <SostituisciModal
          assignment={sostituisciTarget}
          users={userList}
          onClose={() => setSostituisciTarget(null)}
          onSuccess={showToast}
        />
      )}

      {toast && <Toast msg={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
