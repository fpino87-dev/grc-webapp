import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT, type AssetOT, type RegisterChangeResult } from "../../api/endpoints/assets";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

function CriticalityBadge({ value }: { value: number }) {
  const levels: Record<
    number,
    { label: string; desc: string; color: string }
  > = {
    1: {
      label: "Trascurabile",
      color: "bg-green-100 text-green-800",
      desc: "Asset non critico. Fermo tollerato oltre 7 giorni. Nessun BCP richiesto.",
    },
    2: {
      label: "Bassa",
      color: "bg-green-100 text-green-700",
      desc: "Impatto limitato. Fermo tollerato 3-7 giorni. BCP non necessario.",
    },
    3: {
      label: "Media",
      color: "bg-yellow-100 text-yellow-800",
      desc: "Impatto operativo. Fermo tollerato 24-72 ore. BCP consigliato.",
    },
    4: {
      label: "Alta",
      color: "bg-orange-100 text-orange-800",
      desc: "Impatto significativo su produzione o clienti. Fermo tollerato 4-24 ore. BCP obbligatorio.",
    },
    5: {
      label: "Critica",
      color: "bg-red-100 text-red-800",
      desc: "Asset core. Fermo tollerato meno di 4 ore. BCP obbligatorio con test semestrale.",
    },
  };
  const lvl =
    levels[value] ?? {
      label: String(value),
      color: "bg-gray-100 text-gray-600",
      desc: "",
    };
  return (
    <div className="relative group inline-flex">
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded
                        text-xs font-medium cursor-help ${lvl.color}`}
      >
        {value} — {lvl.label}
      </span>
      {lvl.desc && (
        <div
          className="absolute bottom-full left-0 mb-1 w-60 bg-gray-900
                        text-white text-xs rounded p-2 shadow-lg
                        hidden group-hover:block z-50 pointer-events-none"
        >
          {lvl.desc}
        </div>
      )}
    </div>
  );
}

function ChangeBadges({ asset }: { asset: AssetIT | AssetOT }) {
  return (
    <>
      {asset.has_recent_change && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-300 ml-2">
          Change {asset.change_age_days}gg fa
        </span>
      )}
      {asset.needs_revaluation && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-300 ml-2">
          Da rivalutare
        </span>
      )}
    </>
  );
}

function RegisterChangeForm({
  asset,
  assetType,
  onClose,
}: {
  asset: AssetIT | AssetOT;
  assetType: "IT" | "OT";
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [changeRef, setChangeRef] = useState("");
  const [changeDesc, setChangeDesc] = useState("");
  const [portalUrl, setPortalUrl] = useState("");
  const [result, setResult] = useState<RegisterChangeResult | null>(null);

  const registerMutation = useMutation({
    mutationFn: () =>
      assetsApi.registerChange(asset.id, assetType, {
        change_ref: changeRef,
        change_desc: changeDesc,
        portal_url: portalUrl,
      }),
    onSuccess: (res) => {
      setResult(res);
      qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] });
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => assetsApi.clearRevaluation(asset.id, assetType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] });
      onClose();
    },
  });

  return (
    <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 mt-4">
      {/* Existing change info */}
      {asset.last_change_ref && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-amber-800 text-sm">Ultimo change registrato</span>
            {asset.change_portal_url && (
              <a href={asset.change_portal_url} target="_blank" rel="noreferrer" className="text-blue-600 text-sm hover:underline">
                Apri ticket →
              </a>
            )}
          </div>
          <p className="text-sm"><strong>Ref:</strong> {asset.last_change_ref}</p>
          <p className="text-sm"><strong>Data:</strong> {asset.last_change_date ? new Date(asset.last_change_date).toLocaleDateString("it-IT") : "—"}</p>
          <p className="text-sm"><strong>Descrizione:</strong> {asset.last_change_desc || "—"}</p>
          {asset.needs_revaluation && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-red-600">
                Rivalutazione richiesta dal {asset.needs_revaluation_since ? new Date(asset.needs_revaluation_since).toLocaleDateString("it-IT") : "—"}
              </span>
              <button
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
                className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
              >
                Segna come rivalutato
              </button>
            </div>
          )}
        </div>
      )}

      {/* Register change form */}
      {result ? (
        <div className="bg-white rounded border border-green-200 p-3">
          <p className="text-sm font-medium text-green-700 mb-1">Change registrato</p>
          <p className="text-xs text-gray-600">Ref: {result.ref}</p>
          <p className="text-xs text-gray-600">
            Impattati: {result.affected.controls} controlli, {result.affected.risks} risk assessment,{" "}
            {result.affected.processes} processi
          </p>
          <button onClick={onClose} className="mt-2 text-xs text-blue-600 hover:underline">Chiudi</button>
        </div>
      ) : (
        <>
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-2">Registra change</p>
          <div className="space-y-2">
            <input
              value={changeRef}
              onChange={(e) => setChangeRef(e.target.value)}
              placeholder="Riferimento ticket (es. JIRA-1234) *"
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
            <input
              value={changeDesc}
              onChange={(e) => setChangeDesc(e.target.value)}
              placeholder="Descrizione breve del change"
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
            <input
              value={portalUrl}
              onChange={(e) => setPortalUrl(e.target.value)}
              placeholder="URL ticket (opzionale)"
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
          </div>
          {registerMutation.isError && (
            <p className="text-xs text-red-600 mt-1">Errore durante la registrazione</p>
          )}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => registerMutation.mutate()}
              disabled={!changeRef || registerMutation.isPending}
              className="px-3 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-50"
            >
              {registerMutation.isPending ? "Registrazione..." : "Registra"}
            </button>
            <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50">
              Annulla
            </button>
          </div>
        </>
      )}
    </div>
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
            <details className="mt-2 text-xs">
              <summary className="text-blue-600 cursor-pointer hover:underline">
                ℹ️ Come scegliere la criticità
              </summary>
              <table className="mt-2 w-full border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="border px-2 py-1">Valore</th>
                    <th className="border px-2 py-1">Etichetta</th>
                    <th className="border px-2 py-1">Downtime tollerato</th>
                    <th className="border px-2 py-1">BCP</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    [1,"Trascurabile","> 7 giorni","No"],
                    [2,"Bassa","3–7 giorni","No"],
                    [3,"Media","24–72 ore","Consigliato"],
                    [4,"Alta","4–24 ore","Obbligatorio"],
                    [5,"Critica","< 4 ore","Obbligatorio + test semestrale"],
                  ].map(([v,l,d,b]) => (
                    <tr key={v as number}>
                      <td className="border px-2 py-1 text-center font-bold">{v as number}</td>
                      <td className="border px-2 py-1">{l as string}</td>
                      <td className="border px-2 py-1">{d as string}</td>
                      <td className="border px-2 py-1 text-center">{b as string}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
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
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
              Nessun asset IT trovato
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <>
              <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {a.name}
                  <ChangeBadges asset={a} />
                </td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{a.fqdn}</td>
                <td className="px-4 py-3 text-gray-600">{a.os}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3"><StatusBadge status={a.internet_exposed ? "si" : "no"} /></td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {a.eol_date ? new Date(a.eol_date).toLocaleDateString("it-IT") : "—"}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5"
                  >
                    {expandedId === a.id ? "Chiudi" : "Change"}
                  </button>
                </td>
              </tr>
              {expandedId === a.id && (
                <tr key={`${a.id}-detail`}>
                  <td colSpan={7} className="px-4 pb-4">
                    <RegisterChangeForm asset={a} assetType="IT" onClose={() => setExpandedId(null)} />
                  </td>
                </tr>
              )}
            </>
          ))
        )}
      </tbody>
    </table>
  );
}

function OTTab({ search }: { search: string }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
              Nessun asset OT trovato
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <>
              <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {a.name}
                  <ChangeBadges asset={a} />
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {a.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{a.purdue_level}</td>
                <td className="px-4 py-3"><StatusBadge status={a.patchable ? "si" : "no"} /></td>
                <td className="px-4 py-3 text-gray-600">{a.vendor}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5"
                  >
                    {expandedId === a.id ? "Chiudi" : "Change"}
                  </button>
                </td>
              </tr>
              {expandedId === a.id && (
                <tr key={`${a.id}-detail`}>
                  <td colSpan={7} className="px-4 pb-4">
                    <RegisterChangeForm asset={a} assetType="OT" onClose={() => setExpandedId(null)} />
                  </td>
                </tr>
              )}
            </>
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
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Asset IT/OT
          <ModuleHelp
            title="Asset IT e OT — M04"
            description="Censisce tutti gli asset informatici (server, PC, applicativi)
    e operativi (PLC, SCADA, HMI). La criticità determina la priorità
    nelle valutazioni di rischio e l'obbligo di BCP."
            steps={[
              "Crea l'asset indicando tipo IT o OT",
              "Assegna criticità 1-5 (vedi tabella nel form)",
              "Collega ai processi critici della BIA per calcolare l'ALE",
              "Registra change esterni con il bottone 'Registra change'",
              "Il sistema segnala automaticamente gli asset da rivalutare",
            ]}
            connections={[
              { module: "M05 BIA", relation: "Asset collegato a processo critico" },
              { module: "M06 Risk", relation: "Asset oggetto di risk assessment" },
              { module: "M16 BCP", relation: "Asset critico (≥4) richiede piano BCP" },
            ]}
            configNeeded={[
              "Creare prima i Plant in M01",
              "Creare i processi BIA (M05) prima di collegare gli asset",
            ]}
          />
        </h2>
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
