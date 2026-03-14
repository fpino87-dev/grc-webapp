import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersApi, type GrcUser, type GrcRole } from "../../api/endpoints/users";

const roleColors: Record<string, string> = {
  super_admin: "bg-purple-100 text-purple-800",
  compliance_officer: "bg-blue-100 text-blue-800",
  risk_manager: "bg-orange-100 text-orange-800",
  plant_manager: "bg-teal-100 text-teal-800",
  control_owner: "bg-green-100 text-green-800",
  internal_auditor: "bg-yellow-100 text-yellow-800",
  external_auditor: "bg-gray-100 text-gray-600",
};

function RoleBadge({ role }: { role: string | null }) {
  if (!role) return <span className="text-gray-400 text-xs">—</span>;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${roleColors[role] ?? "bg-gray-100 text-gray-600"}`}>
      {role.replace(/_/g, " ")}
    </span>
  );
}

function NewUserModal({ roles, onClose }: { roles: GrcRole[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ username: "", email: "", first_name: "", last_name: "", password: "", grc_role: "" });

  const mutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo utente</h3>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
              <input name="username" value={form.username} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input name="email" type="email" value={form.email} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
              <input name="first_name" value={form.first_name} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cognome</label>
              <input name="last_name" value={form.last_name} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
            <input name="password" type="password" value={form.password} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ruolo GRC</label>
            <select name="grc_role" value={form.grc_role} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— nessuno —</option>
              {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate({ username: form.username, email: form.email, first_name: form.first_name, last_name: form.last_name, password: form.password, grc_role: form.grc_role || undefined })}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea utente"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AssignRoleInline({ user, roles }: { user: GrcUser; roles: GrcRole[] }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState(user.grc_role ?? "");

  const mutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => usersApi.assignRole(id, role),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setOpen(false); },
  });

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5">
        Assegna ruolo
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <select value={role} onChange={e => setRole(e.target.value)} className="border rounded px-2 py-0.5 text-xs">
        <option value="">— nessuno —</option>
        {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
      </select>
      <button
        onClick={() => mutation.mutate({ id: user.id, role })}
        disabled={mutation.isPending}
        className="text-xs bg-primary-600 text-white rounded px-2 py-0.5 hover:bg-primary-700 disabled:opacity-50"
      >
        OK
      </button>
      <button onClick={() => setOpen(false)} className="text-xs text-gray-500 hover:text-gray-700">✕</button>
    </div>
  );
}

export function UsersPage() {
  const [showNew, setShowNew] = useState(false);
  const qc = useQueryClient();

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: usersApi.list,
    retry: false,
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["users-roles"],
    queryFn: usersApi.listRoles,
    retry: false,
  });

  const toggleMutation = useMutation({
    mutationFn: (id: number) => usersApi.toggleActive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Governance — Utenti</h2>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          + Nuovo utente
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun utente trovato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Username</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ruolo GRC</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Attivo</th>
                <th className="px-4 py-3 font-medium text-gray-600">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(user => (
                <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{user.username}</td>
                  <td className="px-4 py-3 text-gray-600">{user.email}</td>
                  <td className="px-4 py-3 text-gray-600">{[user.first_name, user.last_name].filter(Boolean).join(" ") || "—"}</td>
                  <td className="px-4 py-3"><RoleBadge role={user.grc_role} /></td>
                  <td className="px-4 py-3">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${user.is_active ? "bg-green-500" : "bg-red-400"}`} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <AssignRoleInline user={user} roles={roles} />
                      <button
                        onClick={() => toggleMutation.mutate(user.id)}
                        disabled={toggleMutation.isPending}
                        className={`text-xs border rounded px-2 py-0.5 disabled:opacity-50 ${user.is_active ? "text-red-600 border-red-200 hover:bg-red-50" : "text-green-600 border-green-200 hover:bg-green-50"}`}
                      >
                        {user.is_active ? "Disattiva" : "Attiva"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewUserModal roles={roles} onClose={() => setShowNew(false)} />}
    </div>
  );
}
