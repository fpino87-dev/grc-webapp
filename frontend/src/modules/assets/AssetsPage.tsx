import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT, type AssetOT } from "../../api/endpoints/assets";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";

function CriticalityBadge({ value }: { value: number }) {
  const colors: Record<number, string> = {
    1: "bg-green-100 text-green-800",
    2: "bg-green-100 text-green-700",
    3: "bg-yellow-100 text-yellow-800",
    4: "bg-orange-100 text-orange-800",
    5: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        colors[value] ?? "bg-gray-100 text-gray-600"
      }`}
    >
      {value}
    </span>
  );
}

function NewAssetModal({ assetType, plants, onClose }: { assetType: "IT" | "OT"; plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, unknown>>({ asset_type: assetType, criticality: 3 });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: assetType === "IT" ? assetsApi.createIT : assetsApi.createOT,
    onSuccess: () => { qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || "Errore durante il salvataggio"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const v = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked
      : e.target.type === "number" ? Number(e.target.value) : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: v }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo asset {assetType}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— seleziona —</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Criticità (1-5)</label>
            <select name="criticality" defaultValue="3" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          {assetType === "IT" ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">FQDN</label>
                <input name="fqdn" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="server.dominio.it" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sistema operativo</label>
                <input name="os" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="Windows Server 2022" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="internet_exposed" name="internet_exposed" onChange={handleChange} className="rounded" />
                <label htmlFor="internet_exposed" className="text-sm text-gray-700">Esposto su Internet</label>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Categoria *</label>
                <select name="category" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">— seleziona —</option>
                  {["PLC","SCADA","HMI","RTU","sensore","altro"].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Livello Purdue *</label>
                <select name="purdue_level" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">— seleziona —</option>
                  {[0,1,2,3,4].map(n => <option key={n} value={n}>L{n}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Vendor</label>
                <input name="vendor" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
              </div>
            </>
          )}
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form as any)}
            disabled={mutation.isPending || !form.plant || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea asset"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ITTab({ search }: { search: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["assets-it"],
    queryFn: () => assetsApi.listIT(),
    retry: false,
  });

  const assets: AssetIT[] = (data?.results ?? []).filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.fqdn.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">Caricamento...</div>;
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">FQDN</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">OS</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Criticità</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Esposto internet</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">EOL</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
              Nessun asset IT trovato
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <tr key={a.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-medium text-gray-800">{a.name}</td>
              <td className="px-4 py-3 text-gray-600 font-mono text-xs">{a.fqdn}</td>
              <td className="px-4 py-3 text-gray-600">{a.os}</td>
              <td className="px-4 py-3">
                <CriticalityBadge value={a.criticality} />
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={a.internet_exposed ? "si" : "no"} />
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {a.eol_date
                  ? new Date(a.eol_date).toLocaleDateString("it-IT")
                  : "—"}
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

function OTTab({ search }: { search: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["assets-ot"],
    queryFn: () => assetsApi.listOT(),
    retry: false,
  });

  const assets: AssetOT[] = (data?.results ?? []).filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.vendor.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">Caricamento...</div>;
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Categoria</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Livello Purdue</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Patchable</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Vendor</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Criticità</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
              Nessun asset OT trovato
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <tr key={a.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-medium text-gray-800">{a.name}</td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                  {a.category}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600">{a.purdue_level}</td>
              <td className="px-4 py-3">
                <StatusBadge status={a.patchable ? "si" : "no"} />
              </td>
              <td className="px-4 py-3 text-gray-600">{a.vendor}</td>
              <td className="px-4 py-3">
                <CriticalityBadge value={a.criticality} />
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

export function AssetsPage() {
  const [activeTab, setActiveTab] = useState<"IT" | "OT">("IT");
  const [search, setSearch] = useState("");
  const [showNew, setShowNew] = useState(false);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Asset IT/OT</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo asset {activeTab}
        </button>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <div className="flex border-b border-gray-200">
          {(["IT", "OT"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Asset {tab}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Cerca per nome..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto border rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {activeTab === "IT" ? (
          <ITTab search={search} />
        ) : (
          <OTTab search={search} />
        )}
      </div>

      {showNew && plants && (
        <NewAssetModal assetType={activeTab} plants={plants} onClose={() => setShowNew(false)} />
      )}
    </div>
  );
}
