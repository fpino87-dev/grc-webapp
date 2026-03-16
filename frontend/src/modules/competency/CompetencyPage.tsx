import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { usersApi, type GrcUser } from "../../api/endpoints/users";

// ── Types ────────────────────────────────────────────────────────────────────

interface RoleRequirement {
  id: string;
  grc_role: string;
  competency: string;
  required_level: number;
  evidence_type: string;
  mandatory: boolean;
  notes: string;
}

interface UserCompetency {
  id: string;
  user: number;
  competency: string;
  level: number;
  evidence_type: string;
  certification_body: string;
  obtained_at: string | null;
  valid_until: string | null;
  is_valid: boolean;
  verified_by_name: string | null;
}

// ── Constants ────────────────────────────────────────────────────────────────

const ROLES: { value: string; label: string }[] = [
  { value: "ciso",                label: "CISO" },
  { value: "compliance_officer",  label: "Compliance Officer" },
  { value: "risk_manager",        label: "Risk Manager" },
  { value: "internal_auditor",    label: "Internal Auditor" },
  { value: "plant_manager",       label: "Plant Manager" },
  { value: "control_owner",       label: "Control Owner" },
  { value: "external_auditor",    label: "External Auditor" },
];

const EVIDENCE_TYPES = [
  { value: "certification",  label: "Certificazione" },
  { value: "training",       label: "Training" },
  { value: "experience",     label: "Esperienza" },
  { value: "assessment",     label: "Assessment" },
];

const LEVEL_LABELS: Record<number, string> = {
  1: "1 — Awareness",
  2: "2 — Practitioner",
  3: "3 — Expert",
};

const LEVEL_COLORS: Record<number, string> = {
  1: "bg-blue-100 text-blue-800",
  2: "bg-yellow-100 text-yellow-800",
  3: "bg-green-100 text-green-800",
};

// ── API helpers ───────────────────────────────────────────────────────────────

const reqApi = {
  list: () =>
    apiClient.get<{ results: RoleRequirement[] }>("/auth/competency-requirements/?page_size=200")
      .then(r => r.data.results ?? r.data),
  create: (d: Omit<RoleRequirement, "id">) =>
    apiClient.post<RoleRequirement>("/auth/competency-requirements/", d).then(r => r.data),
  update: (id: string, d: Partial<RoleRequirement>) =>
    apiClient.patch<RoleRequirement>(`/auth/competency-requirements/${id}/`, d).then(r => r.data),
  remove: (id: string) =>
    apiClient.delete(`/auth/competency-requirements/${id}/`),
};

const ucApi = {
  list: () =>
    apiClient.get<{ results: UserCompetency[] }>("/auth/user-competencies/?page_size=500")
      .then(r => r.data.results ?? r.data),
  create: (d: Partial<UserCompetency> & { user: number }) =>
    apiClient.post<UserCompetency>("/auth/user-competencies/", d).then(r => r.data),
  update: (id: string, d: Partial<UserCompetency>) =>
    apiClient.patch<UserCompetency>(`/auth/user-competencies/${id}/`, d).then(r => r.data),
  remove: (id: string) =>
    apiClient.delete(`/auth/user-competencies/${id}/`),
};

// ── Level badge ───────────────────────────────────────────────────────────────

function LevelBadge({ level }: { level: number }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LEVEL_COLORS[level] ?? "bg-gray-100 text-gray-700"}`}>
      {LEVEL_LABELS[level] ?? level}
    </span>
  );
}

// ── Tab 1: Requisiti per ruolo ────────────────────────────────────────────────

function RequirementsTab() {
  const qc = useQueryClient();
  const { data: requirements = [], isLoading } = useQuery({
    queryKey: ["competency-requirements"],
    queryFn: reqApi.list,
  });

  const [filterRole, setFilterRole] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<RoleRequirement | null>(null);
  const [form, setForm] = useState({
    grc_role: "", competency: "", required_level: 2,
    evidence_type: "training", mandatory: true, notes: "",
  });

  const filtered = filterRole
    ? requirements.filter(r => r.grc_role === filterRole)
    : requirements;

  const grouped = ROLES.map(role => ({
    role,
    items: filtered.filter(r => r.grc_role === role.value),
  })).filter(g => !filterRole || g.role.value === filterRole || g.items.length > 0);

  const saveMutation = useMutation({
    mutationFn: () =>
      editItem
        ? reqApi.update(editItem.id, form)
        : reqApi.create(form as Omit<RoleRequirement, "id">),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["competency-requirements"] });
      setShowForm(false);
      setEditItem(null);
      setForm({ grc_role: "", competency: "", required_level: 2, evidence_type: "training", mandatory: true, notes: "" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: reqApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["competency-requirements"] }),
  });

  function openNew() {
    setEditItem(null);
    setForm({ grc_role: filterRole, competency: "", required_level: 2, evidence_type: "training", mandatory: true, notes: "" });
    setShowForm(true);
  }

  function openEdit(r: RoleRequirement) {
    setEditItem(r);
    setForm({
      grc_role: r.grc_role, competency: r.competency,
      required_level: r.required_level, evidence_type: r.evidence_type,
      mandatory: r.mandatory, notes: r.notes,
    });
    setShowForm(true);
  }

  if (isLoading) return <p className="text-sm text-gray-500 p-4">Caricamento...</p>;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={filterRole}
          onChange={e => setFilterRole(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm"
        >
          <option value="">Tutti i ruoli</option>
          {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
        <button
          onClick={openNew}
          className="ml-auto bg-primary-600 text-white px-3 py-1.5 rounded text-sm hover:bg-primary-700"
        >
          + Nuovo requisito
        </button>
      </div>

      {/* Form modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg space-y-4">
            <h3 className="font-semibold text-lg">
              {editItem ? "Modifica requisito" : "Nuovo requisito"}
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Ruolo</label>
                <select
                  value={form.grc_role}
                  onChange={e => setForm(f => ({ ...f, grc_role: e.target.value }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                >
                  <option value="">— seleziona —</option>
                  {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Livello richiesto</label>
                <select
                  value={form.required_level}
                  onChange={e => setForm(f => ({ ...f, required_level: Number(e.target.value) }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                >
                  {[1, 2, 3].map(l => <option key={l} value={l}>{LEVEL_LABELS[l]}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Competenza</label>
              <input
                value={form.competency}
                onChange={e => setForm(f => ({ ...f, competency: e.target.value }))}
                className="border rounded px-2 py-1.5 text-sm w-full"
                placeholder="es. ISO 27001 Lead Implementer"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tipo evidenza</label>
                <select
                  value={form.evidence_type}
                  onChange={e => setForm(f => ({ ...f, evidence_type: e.target.value }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                >
                  {EVIDENCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2 mt-5">
                <input
                  type="checkbox"
                  id="mandatory"
                  checked={form.mandatory}
                  onChange={e => setForm(f => ({ ...f, mandatory: e.target.checked }))}
                />
                <label htmlFor="mandatory" className="text-sm">Obbligatorio</label>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Note</label>
              <textarea
                value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                className="border rounded px-2 py-1.5 text-sm w-full"
                rows={2}
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => { setShowForm(false); setEditItem(null); }}
                className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50"
              >
                Annulla
              </button>
              <button
                onClick={() => saveMutation.mutate()}
                disabled={!form.grc_role || !form.competency || saveMutation.isPending}
                className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? "Salvataggio..." : "Salva"}
              </button>
            </div>
            {saveMutation.isError && (
              <p className="text-red-600 text-xs">Errore durante il salvataggio.</p>
            )}
          </div>
        </div>
      )}

      {/* Tables by role */}
      {grouped.map(({ role, items }) => {
        const shown = filterRole ? filtered : items;
        const rows = filterRole ? shown : items;
        if (rows.length === 0 && filterRole) return null;
        if (rows.length === 0) return null;
        return (
          <div key={role.value} className="bg-white rounded-lg border">
            <div className="px-4 py-2 border-b bg-gray-50 flex items-center justify-between">
              <span className="font-semibold text-sm text-gray-700">{role.label}</span>
              <span className="text-xs text-gray-400">{rows.length} requisiti</span>
            </div>
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 border-b">
                <tr>
                  <th className="text-left px-4 py-2">Competenza</th>
                  <th className="text-left px-4 py-2">Livello</th>
                  <th className="text-left px-4 py-2">Evidenza</th>
                  <th className="text-left px-4 py-2">Obbl.</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{r.competency}</td>
                    <td className="px-4 py-2"><LevelBadge level={r.required_level} /></td>
                    <td className="px-4 py-2 text-gray-600">
                      {EVIDENCE_TYPES.find(t => t.value === r.evidence_type)?.label ?? r.evidence_type}
                    </td>
                    <td className="px-4 py-2">
                      {r.mandatory
                        ? <span className="text-green-600 font-bold">✓</span>
                        : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-2 text-right space-x-2 whitespace-nowrap">
                      <button
                        onClick={() => openEdit(r)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Modifica
                      </button>
                      <button
                        onClick={() => {
                          if (confirm("Eliminare questo requisito?")) deleteMutation.mutate(r.id);
                        }}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Elimina
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}

      {filtered.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-8">Nessun requisito trovato.</p>
      )}
    </div>
  );
}

// ── Tab 2: Competenze utenti ──────────────────────────────────────────────────

function UserCompetenciesTab() {
  const qc = useQueryClient();
  const { data: competencies = [], isLoading: loadingComp } = useQuery({
    queryKey: ["user-competencies"],
    queryFn: ucApi.list,
  });
  const { data: users = [], isLoading: loadingUsers } = useQuery({
    queryKey: ["users"],
    queryFn: usersApi.list,
  });

  const [filterUser, setFilterUser] = useState<number | "">("");
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<UserCompetency | null>(null);
  const [form, setForm] = useState({
    user: "" as number | "",
    competency: "",
    level: 1,
    evidence_type: "training",
    certification_body: "",
    obtained_at: "",
    valid_until: "",
  });

  const usersById: Record<number, GrcUser> = {};
  users.forEach(u => { usersById[u.id] = u; });

  const filtered = filterUser
    ? competencies.filter(c => c.user === filterUser)
    : competencies;

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        ...form,
        user: form.user as number,
        obtained_at: form.obtained_at || null,
        valid_until: form.valid_until || null,
        certification_body: form.certification_body || "",
      };
      return editItem
        ? ucApi.update(editItem.id, payload)
        : ucApi.create(payload as UserCompetency & { user: number });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["user-competencies"] });
      setShowForm(false);
      setEditItem(null);
      setForm({ user: "", competency: "", level: 1, evidence_type: "training", certification_body: "", obtained_at: "", valid_until: "" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ucApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["user-competencies"] }),
  });

  function openNew() {
    setEditItem(null);
    setForm({ user: filterUser || "", competency: "", level: 1, evidence_type: "training", certification_body: "", obtained_at: "", valid_until: "" });
    setShowForm(true);
  }

  function openEdit(c: UserCompetency) {
    setEditItem(c);
    setForm({
      user: c.user,
      competency: c.competency,
      level: c.level,
      evidence_type: c.evidence_type,
      certification_body: c.certification_body ?? "",
      obtained_at: c.obtained_at ?? "",
      valid_until: c.valid_until ?? "",
    });
    setShowForm(true);
  }

  function userName(id: number) {
    const u = usersById[id];
    if (!u) return `ID ${id}`;
    return `${u.first_name} ${u.last_name}`.trim() || u.username || u.email;
  }

  function validityBadge(c: UserCompetency) {
    if (!c.valid_until) return null;
    const days = Math.ceil((new Date(c.valid_until).getTime() - Date.now()) / 86400000);
    if (days < 0) return <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">Scaduta</span>;
    if (days < 90) return <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">Scade in {days}gg</span>;
    return <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">Valida</span>;
  }

  if (loadingComp || loadingUsers) return <p className="text-sm text-gray-500 p-4">Caricamento...</p>;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={filterUser}
          onChange={e => setFilterUser(e.target.value ? Number(e.target.value) : "")}
          className="border rounded px-3 py-1.5 text-sm"
        >
          <option value="">Tutti gli utenti</option>
          {users.map(u => (
            <option key={u.id} value={u.id}>
              {`${u.first_name} ${u.last_name}`.trim() || u.username || u.email}
            </option>
          ))}
        </select>
        <button
          onClick={openNew}
          className="ml-auto bg-primary-600 text-white px-3 py-1.5 rounded text-sm hover:bg-primary-700"
        >
          + Aggiungi competenza
        </button>
      </div>

      {/* Form modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg space-y-4">
            <h3 className="font-semibold text-lg">
              {editItem ? "Modifica competenza" : "Aggiungi competenza utente"}
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Utente</label>
                <select
                  value={form.user}
                  onChange={e => setForm(f => ({ ...f, user: Number(e.target.value) }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                  disabled={!!editItem}
                >
                  <option value="">— seleziona —</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>
                      {`${u.first_name} ${u.last_name}`.trim() || u.username}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Livello</label>
                <select
                  value={form.level}
                  onChange={e => setForm(f => ({ ...f, level: Number(e.target.value) }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                >
                  {[1, 2, 3].map(l => <option key={l} value={l}>{LEVEL_LABELS[l]}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Competenza</label>
              <input
                value={form.competency}
                onChange={e => setForm(f => ({ ...f, competency: e.target.value }))}
                className="border rounded px-2 py-1.5 text-sm w-full"
                placeholder="es. ISO 27001 Lead Implementer"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tipo evidenza</label>
                <select
                  value={form.evidence_type}
                  onChange={e => setForm(f => ({ ...f, evidence_type: e.target.value }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                >
                  {EVIDENCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Ente certificatore</label>
                <input
                  value={form.certification_body}
                  onChange={e => setForm(f => ({ ...f, certification_body: e.target.value }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                  placeholder="es. BSI, Bureau Veritas"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data conseguimento</label>
                <input
                  type="date"
                  value={form.obtained_at}
                  onChange={e => setForm(f => ({ ...f, obtained_at: e.target.value }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Scadenza</label>
                <input
                  type="date"
                  value={form.valid_until}
                  onChange={e => setForm(f => ({ ...f, valid_until: e.target.value }))}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => { setShowForm(false); setEditItem(null); }}
                className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50"
              >
                Annulla
              </button>
              <button
                onClick={() => saveMutation.mutate()}
                disabled={!form.user || !form.competency || saveMutation.isPending}
                className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? "Salvataggio..." : "Salva"}
              </button>
            </div>
            {saveMutation.isError && (
              <p className="text-red-600 text-xs">Errore durante il salvataggio.</p>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-gray-500 border-b bg-gray-50">
            <tr>
              <th className="text-left px-4 py-2">Utente</th>
              <th className="text-left px-4 py-2">Competenza</th>
              <th className="text-left px-4 py-2">Livello</th>
              <th className="text-left px-4 py-2">Evidenza</th>
              <th className="text-left px-4 py-2">Conseguita</th>
              <th className="text-left px-4 py-2">Validità</th>
              <th className="text-left px-4 py-2">Verificata da</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center py-8 text-gray-400 text-sm">
                  Nessuna competenza registrata.
                </td>
              </tr>
            )}
            {filtered.map(c => (
              <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{userName(c.user)}</td>
                <td className="px-4 py-2">{c.competency}</td>
                <td className="px-4 py-2"><LevelBadge level={c.level} /></td>
                <td className="px-4 py-2 text-gray-600">
                  {EVIDENCE_TYPES.find(t => t.value === c.evidence_type)?.label ?? c.evidence_type}
                  {c.certification_body && <span className="text-gray-400 ml-1">({c.certification_body})</span>}
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {c.obtained_at ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-4 py-2">
                  {validityBadge(c) ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-4 py-2 text-gray-500 text-xs">
                  {c.verified_by_name ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-4 py-2 text-right space-x-2 whitespace-nowrap">
                  <button
                    onClick={() => openEdit(c)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Modifica
                  </button>
                  <button
                    onClick={() => {
                      if (confirm("Eliminare questa competenza?")) deleteMutation.mutate(c.id);
                    }}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Elimina
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function CompetencyPage() {
  const [tab, setTab] = useState<"requirements" | "users">("requirements");

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Competenze</h1>
        <p className="text-sm text-gray-500 mt-1">
          ISO 27001 § 7.2 — Requisiti di competenza per ruolo e tracciamento competenze individuali.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-0">
        {(["requirements", "users"] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-primary-600 text-primary-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "requirements" ? "Requisiti per ruolo" : "Competenze utenti"}
          </button>
        ))}
      </div>

      {tab === "requirements" ? <RequirementsTab /> : <UserCompetenciesTab />}
    </div>
  );
}
