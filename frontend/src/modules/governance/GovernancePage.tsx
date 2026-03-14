import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { governanceApi, type RoleAssignment, type SecurityCommittee } from "../../api/endpoints/governance";
import { usersApi } from "../../api/endpoints/users";
import { StatusBadge } from "../../components/ui/StatusBadge";

const ROLE_LABELS: Record<string, string> = {
  ciso: "CISO",
  plant_security_officer: "Plant Security Officer",
  nis2_contact: "NIS2 Contact",
  dpo: "DPO",
  isms_manager: "ISMS Manager",
  internal_auditor: "Internal Auditor",
  comitato_membro: "Membro Comitato",
  bu_referente: "BU Referente",
  raci_responsible: "RACI Responsible",
  raci_accountable: "RACI Accountable",
};

function RoleAssignmentModal({ users, onClose }: { users: { id: number; email: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<RoleAssignment & { valid_from: string }>>({
    scope_type: "org",
    valid_from: new Date().toISOString().slice(0, 10),
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: governanceApi.createRoleAssignment,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["role-assignments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value || null }));
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
              {users.map(u => <option key={u.id} value={u.id}>{u.email}</option>)}
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
              <option value="org">Organizzazione</option>
              <option value="bu">Business Unit</option>
              <option value="plant">Sito</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valido dal *</label>
              <input type="date" name="valid_from" defaultValue={form.valid_from as string} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valido fino al</label>
              <input type="date" name="valid_until" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.user || !form.role || !form.valid_from}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Assegna ruolo"}
          </button>
        </div>
      </div>
    </div>
  );
}

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
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="es. Comitato per la Sicurezza" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select name="committee_type" defaultValue="centrale" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="centrale">Centrale</option>
                <option value="bu">BU</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequenza</label>
              <select name="frequency" defaultValue="trimestrale" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="mensile">Mensile</option>
                <option value="trimestrale">Trimestrale</option>
                <option value="semestrale">Semestrale</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prossima riunione</label>
            <input type="datetime-local" name="next_meeting_at" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
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

export function GovernancePage() {
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [showCommitteeModal, setShowCommitteeModal] = useState(false);

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

  const userList = (users ?? []).map(u => ({ id: u.id, email: u.email }));

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Governance</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ruoli normativi */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Ruoli normativi</h3>
            <button onClick={() => setShowRoleModal(true)} className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
              + Assegna
            </button>
          </div>
          {loadingAssign ? (
            <p className="text-sm text-gray-400">Caricamento...</p>
          ) : !assignments?.length ? (
            <p className="text-sm text-gray-400 italic">Nessun ruolo assegnato</p>
          ) : (
            <div className="space-y-2">
              {assignments.map((a) => (
                <div key={a.id} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
                  <div>
                    <span className="font-medium text-gray-800">
                      {ROLE_LABELS[a.role] ?? a.role}
                    </span>
                    <span className="text-xs text-gray-400 ml-2">{a.user_email ?? a.user}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {a.valid_until
                        ? `fino al ${new Date(a.valid_until).toLocaleDateString("it-IT")}`
                        : "senza scadenza"}
                    </span>
                    <StatusBadge status={a.is_active ? "attivo" : "chiuso"} />
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
            <button onClick={() => setShowCommitteeModal(true)} className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
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
                      <> — prossima riunione:{" "}
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

      {showRoleModal && <RoleAssignmentModal users={userList} onClose={() => setShowRoleModal(false)} />}
      {showCommitteeModal && <CommitteeModal onClose={() => setShowCommitteeModal(false)} />}
    </div>
  );
}
