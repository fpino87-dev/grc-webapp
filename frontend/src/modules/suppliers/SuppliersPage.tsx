import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { StatusBadge } from "../../components/ui/StatusBadge";

function NewSupplierModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({ risk_level: "basso", status: "attivo" });

  const mutation = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo fornitore</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">P.IVA</label>
              <input name="vat_number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paese</label>
              <input name="country" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="IT" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Livello rischio</label>
              <select name="risk_level" defaultValue="basso" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Scadenza contratto</label>
              <input name="contract_expiry" type="date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea fornitore"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ExpiryCell({ date }: { date: string | null }) {
  if (!date) return <span className="text-gray-400">—</span>;
  const daysLeft = Math.ceil((new Date(date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  const isNear = daysLeft < 30;
  return (
    <span className={isNear ? "text-red-600 font-medium" : "text-gray-600"}>
      {new Date(date).toLocaleDateString("it-IT")}
      {isNear && <span className="ml-1 text-xs">({daysLeft}gg)</span>}
    </span>
  );
}

export function SuppliersPage() {
  const [showNew, setShowNew] = useState(false);
  const [filterRisk, setFilterRisk] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const params: Record<string, string> = {};
  if (filterRisk) params.risk_level = filterRisk;
  if (filterStatus) params.status = filterStatus;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", filterRisk, filterStatus],
    queryFn: () => suppliersApi.list(Object.keys(params).length ? params : undefined),
    retry: false,
  });

  const suppliers = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Operazioni — Fornitori</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo fornitore
        </button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-600">Rischio:</label>
        <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">Tutti</option>
          {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <label className="text-sm text-gray-600 ml-2">Stato:</label>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">Tutti</option>
          {["attivo","sospeso","terminato"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : suppliers.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun fornitore trovato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">P.IVA</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Paese</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rischio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scadenza contratto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {suppliers.map(s => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{s.name}</td>
                  <td className="px-4 py-3 text-gray-600">{s.vat_number || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{s.country || "—"}</td>
                  <td className="px-4 py-3"><StatusBadge status={s.risk_level} /></td>
                  <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                  <td className="px-4 py-3"><ExpiryCell date={s.contract_expiry} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewSupplierModal onClose={() => setShowNew(false)} />}
    </div>
  );
}
