import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scheduleApi, RequiredDocItem, RequiredDocumentCatalog } from "../../api/endpoints/schedule";
import { plantsApi } from "../../api/endpoints/plants";
import { controlsApi } from "../../api/endpoints/controls";
import { useAuthStore } from "../../store/auth";

const FRAMEWORK_LABELS: Record<string, string> = {
  ISO27001: "ISO 27001",
  NIS2:     "NIS2",
  ACN_NIS2: "ACN NIS2",
  TISAX_L2: "TISAX L2",
  TISAX_L3: "TISAX L3",
  TISAX_PROTO: "TISAX Prototype",
};

const TRAFFIC_LIGHT_COLORS: Record<string, { bg: string; text: string }> = {
  green:  { bg: "bg-green-500",  text: "text-white" },
  yellow: { bg: "bg-yellow-400", text: "text-gray-900" },
  red:    { bg: "bg-red-500",    text: "text-white" },
};

function LinkPickerModal({ item, plantId, onClose }: { item: RequiredDocItem; plantId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<{ kind: "document" | "evidence"; id: string } | null>(null);
  const [error, setError] = useState("");

  const { data: linkables, isLoading } = useQuery({
    queryKey: ["required-doc-linkables", plantId, item.id],
    queryFn: () => scheduleApi.getRequiredDocLinkables({ plant: plantId, required_document: item.id }),
    retry: false,
  });

  const linkMutation = useMutation({
    mutationFn: () =>
      scheduleApi.linkRequiredDoc({
        plant: plantId,
        required_document: item.id,
        document: selected?.kind === "document" ? selected.id : undefined,
        evidence: selected?.kind === "evidence" ? selected.id : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["required-docs-status"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error || "Errore durante il collegamento";
      setError(String(msg));
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: () => scheduleApi.unlinkRequiredDoc({ plant: plantId, required_document: item.id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["required-docs-status"] });
      onClose();
    },
  });

  const hasControl = !!linkables?.control;
  const docs = linkables?.documents ?? [];
  const evs = linkables?.evidences ?? [];
  const empty = hasControl && docs.length === 0 && evs.length === 0;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg my-8">
        <div className="px-5 py-3 border-b border-gray-200">
          <h3 className="text-base font-semibold text-gray-900">Collega documento / evidenza</h3>
          <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
          {item.control && (
            <p className="text-[11px] text-gray-500 mt-1">
              Controllo: <span className="font-mono text-indigo-700">{item.control.external_id}</span> — {item.control.title}
            </p>
          )}
        </div>

        <div className="px-5 py-4 max-h-[55vh] overflow-y-auto">
          {item.fulfillment && (
            <div className="mb-4 rounded border border-green-200 bg-green-50 p-3 text-xs">
              <div className="font-medium text-green-800">Attualmente collegato</div>
              <div className="text-green-900 mt-0.5">
                {item.fulfillment.kind === "document" ? "📄" : "📎"} {item.fulfillment.title}
                {" · "}<span className="text-green-700">{item.fulfillment.status}</span>
                {item.fulfillment.linked_by && <span className="text-green-600"> · {item.fulfillment.linked_by}</span>}
              </div>
              <button
                type="button"
                onClick={() => unlinkMutation.mutate()}
                disabled={unlinkMutation.isPending}
                className="mt-2 text-[11px] text-red-600 hover:underline"
              >
                Scollega
              </button>
            </div>
          )}

          {isLoading ? (
            <p className="text-sm text-gray-400">Caricamento…</p>
          ) : !hasControl ? (
            item.control_status === "system" ? (
              <div className="text-sm text-blue-800 bg-blue-50 border border-blue-200 rounded px-3 py-2.5">
                <div className="font-medium mb-0.5">Documento di sistema</div>
                Questo requisito non è legato a un controllo specifico (è una clausola gestionale,
                es. Dichiarazione di Applicabilità, riesame della direzione, rapporti di audit interno):
                non va collegato a un controllo. Risulta soddisfatto quando nel sito esiste un
                documento <em>approvato</em> del tipo richiesto (<span className="font-mono">{item.document_type}</span>).
              </div>
            ) : (
              <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2.5">
                <div className="font-medium mb-0.5">Controllo non attivo su questo sito</div>
                Il controllo {item.iso_clause && <span className="font-mono">{item.iso_clause}</span>} collegato a questo
                requisito non è istanziato su questo sito (per classificazione o perimetro): qui non ci sono
                elementi collegabili. Attiva/istanzia il controllo nel modulo Controlli per poterlo soddisfare.
              </div>
            )
          ) : empty ? (
            <p className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded px-3 py-2">
              Nessun documento o evidenza è collegato al controllo <span className="font-mono">{linkables?.control?.external_id}</span>.
              Collega prima l'elemento al controllo nel modulo Controlli, poi torna qui.
            </p>
          ) : (
            <div className="space-y-4">
              {docs.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Documenti</div>
                  <div className="space-y-1">
                    {docs.map(d => (
                      <label key={d.id} className="flex items-center gap-2 p-2 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer">
                        <input type="radio" name="linktarget" checked={selected?.kind === "document" && selected.id === d.id} onChange={() => setSelected({ kind: "document", id: d.id })} />
                        <span className="text-sm text-gray-800">📄 {d.title}</span>
                        <span className={`ml-auto text-[11px] px-1.5 py-0.5 rounded ${d.status === "approvato" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>{d.status}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              {evs.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Evidenze</div>
                  <div className="space-y-1">
                    {evs.map(e => (
                      <label key={e.id} className="flex items-center gap-2 p-2 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer">
                        <input type="radio" name="linktarget" checked={selected?.kind === "evidence" && selected.id === e.id} onChange={() => setSelected({ kind: "evidence", id: e.id })} />
                        <span className="text-sm text-gray-800">📎 {e.title}</span>
                        <span className={`ml-auto text-[11px] px-1.5 py-0.5 rounded ${e.valid ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                          {e.valid ? "valida" : "scaduta"}{e.valid_until ? ` · ${e.valid_until}` : ""}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        </div>

        <div className="px-5 py-3 border-t border-gray-200 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-600 hover:bg-gray-50">
            Chiudi
          </button>
          <button
            type="button"
            onClick={() => { setError(""); linkMutation.mutate(); }}
            disabled={!selected || linkMutation.isPending}
            className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {linkMutation.isPending ? "Collegamento…" : "Collega e soddisfa"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DocRow({ item, plantId }: { item: RequiredDocItem; plantId: string }) {
  const { t } = useTranslation();
  const [pickerOpen, setPickerOpen] = useState(false);
  const tl = TRAFFIC_LIGHT_COLORS[item.traffic_light] ?? TRAFFIC_LIGHT_COLORS.red;
  const tlLabelKey = item.traffic_light === "green"
    ? "schedule.required_docs.traffic_present_approved"
    : item.traffic_light === "yellow"
    ? "schedule.required_docs.traffic_draft"
    : "schedule.required_docs.traffic_missing";
  const tlLabel = t(tlLabelKey);

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-3 h-3 rounded-full ${tl.bg}`} title={tlLabel} />
          <span className="text-sm font-medium text-gray-900">{item.description}</span>
          {item.mandatory && (
            <span className="text-xs bg-red-100 text-red-700 px-1 py-0.5 rounded">
              {t("schedule.required_docs.mandatory_badge")}
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{item.document_type}</td>
      <td className="px-4 py-3 text-sm text-gray-500 font-mono">{item.iso_clause}</td>
      <td className="px-4 py-3 text-sm">
        {item.fulfillment ? (
          <div>
            <span className="text-gray-800">
              {item.fulfillment.kind === "document" ? "📄" : "📎"} {item.fulfillment.title}
            </span>
            <span className="block text-[11px] text-gray-500 mt-0.5">
              Collegato{item.fulfillment.linked_by ? ` da ${item.fulfillment.linked_by}` : ""}
              {" · "}{item.fulfillment.status}
            </span>
          </div>
        ) : item.document ? (
          <div>
            <span className="text-gray-800">{item.document.title}</span>
            {item.document.review_due_date && (
              <span className="block text-xs text-gray-500 mt-0.5">
                {t("schedule.required_docs.review_date", { date: item.document.review_due_date })}
              </span>
            )}
          </div>
        ) : (
          <span className="text-red-500 italic text-xs">{t("schedule.required_docs.no_doc")}</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${tl.bg} ${tl.text}`}>
            {tlLabel}
          </span>
          <button
            type="button"
            onClick={() => setPickerOpen(true)}
            title={item.control_status === "system"
              ? "Documento di sistema (non legato a un controllo) — dettagli"
              : "Collega documento/evidenza al controllo per soddisfare il requisito"}
            className="text-gray-400 hover:text-blue-600 text-base leading-none"
          >
            {item.control_status === "system" ? "ℹ️" : "🔗"}
          </button>
        </div>
      </td>
      {pickerOpen && <LinkPickerModal item={item} plantId={plantId} onClose={() => setPickerOpen(false)} />}
    </tr>
  );
}

const DOC_TYPES = [
  { value: "policy", label: "Policy" },
  { value: "procedure", label: "Procedura" },
  { value: "record", label: "Registro/Record" },
];

type CatalogForm = {
  document_type: string;
  description: string;
  iso_clause: string;
  mandatory: boolean;
  notes: string;
};

const EMPTY_FORM: CatalogForm = { document_type: "procedure", description: "", iso_clause: "", mandatory: true, notes: "" };

function CatalogManagerModal({ framework, onClose }: { framework: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CatalogForm>(EMPTY_FORM);
  const [error, setError] = useState("");

  const { data: rows, isLoading } = useQuery({
    queryKey: ["required-docs-catalog", framework],
    queryFn: () => scheduleApi.listRequiredDocuments(framework),
    retry: false,
  });
  const { data: controls } = useQuery({
    queryKey: ["framework-controls", framework],
    queryFn: () => scheduleApi.getFrameworkControls(framework),
    retry: false,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["required-docs-catalog", framework] });
    qc.invalidateQueries({ queryKey: ["required-docs-status"] });
  };

  const resetForm = () => { setEditingId(null); setForm(EMPTY_FORM); setError(""); };

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = { ...form, framework };
      return editingId
        ? scheduleApi.updateRequiredDocument(editingId, payload)
        : scheduleApi.createRequiredDocument(payload);
    },
    onSuccess: () => { invalidate(); resetForm(); },
    onError: (e: unknown) => {
      const d = (e as { response?: { status?: number; data?: Record<string, unknown> } })?.response;
      setError(d?.status === 403 ? "Permesso negato: serve il ruolo Compliance Officer o Super Admin." : "Errore durante il salvataggio.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => scheduleApi.deleteRequiredDocument(id),
    onSuccess: invalidate,
    onError: () => setError("Errore durante l'eliminazione."),
  });

  const startEdit = (r: RequiredDocumentCatalog) => {
    setEditingId(r.id);
    setForm({ document_type: r.document_type, description: r.description, iso_clause: r.iso_clause, mandatory: r.mandatory, notes: r.notes || "" });
    setError("");
  };

  const canSave = form.description.trim().length >= 3 && !!form.document_type;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl my-6">
        <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900">
            Gestione catalogo — {FRAMEWORK_LABELS[framework] ?? framework}
          </h3>
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-600 hover:bg-gray-50">Chiudi</button>
        </div>

        <div className="px-5 py-4 max-h-[70vh] overflow-y-auto">
          {/* Form aggiungi/modifica */}
          <div className="border border-gray-200 rounded-lg p-3 mb-4 bg-gray-50">
            <div className="text-xs font-semibold text-gray-600 uppercase mb-2">
              {editingId ? "Modifica documento" : "Aggiungi documento"}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs text-gray-600 col-span-2">
                Descrizione *
                <input
                  className="mt-0.5 w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Es. Policy di gestione del rischio di cybersecurity"
                />
              </label>
              <label className="text-xs text-gray-600">
                Tipo *
                <select
                  className="mt-0.5 w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                  value={form.document_type}
                  onChange={e => setForm(f => ({ ...f, document_type: e.target.value }))}
                >
                  {DOC_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
              <label className="text-xs text-gray-600">
                Controllo collegato
                <select
                  className="mt-0.5 w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                  value={form.iso_clause}
                  onChange={e => setForm(f => ({ ...f, iso_clause: e.target.value }))}
                >
                  <option value="">— nessuno (documento di sistema) —</option>
                  {(controls ?? []).map(c => (
                    <option key={c.external_id} value={c.external_id}>
                      {c.external_id}{c.level ? ` [${c.level}]` : ""} — {c.title.slice(0, 60)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-gray-600 flex items-center gap-2 mt-2">
                <input type="checkbox" checked={form.mandatory} onChange={e => setForm(f => ({ ...f, mandatory: e.target.checked }))} />
                Obbligatorio
              </label>
              <label className="text-xs text-gray-600 col-span-2">
                Note
                <input
                  className="mt-0.5 w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                  value={form.notes}
                  onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                />
              </label>
            </div>
            {error && <p className="text-xs text-red-600 bg-red-50 px-2 py-1.5 rounded mt-2">{error}</p>}
            <div className="flex justify-end gap-2 mt-3">
              {editingId && (
                <button type="button" onClick={resetForm} className="px-3 py-1.5 text-xs border border-gray-300 rounded text-gray-600 hover:bg-gray-50">Annulla</button>
              )}
              <button
                type="button"
                onClick={() => { setError(""); saveMutation.mutate(); }}
                disabled={!canSave || saveMutation.isPending}
                className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? "Salvataggio…" : editingId ? "Salva modifiche" : "Aggiungi"}
              </button>
            </div>
          </div>

          {/* Lista catalogo */}
          {isLoading ? (
            <p className="text-sm text-gray-400">Caricamento…</p>
          ) : (rows ?? []).length === 0 ? (
            <p className="text-sm text-gray-400 italic">Nessun documento nel catalogo per questo framework.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                  <th className="py-2">Documento</th>
                  <th className="py-2">Tipo</th>
                  <th className="py-2">Controllo</th>
                  <th className="py-2">Obbl.</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(rows ?? []).map(r => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="py-2 pr-2 text-gray-800">{r.description}</td>
                    <td className="py-2 pr-2 text-gray-600">{r.document_type}</td>
                    <td className="py-2 pr-2 text-gray-500 font-mono text-xs">{r.iso_clause || "—"}</td>
                    <td className="py-2 pr-2">{r.mandatory ? "Sì" : "No"}</td>
                    <td className="py-2 text-right whitespace-nowrap">
                      <button type="button" onClick={() => startEdit(r)} title="Modifica" className="px-1.5 text-gray-500 hover:text-blue-600">✏️</button>
                      <button
                        type="button"
                        onClick={() => { if (confirm(`Eliminare "${r.description}" dal catalogo?`)) deleteMutation.mutate(r.id); }}
                        title="Elimina"
                        className="px-1.5 text-gray-500 hover:text-red-600"
                      >🗑️</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export function RequiredDocumentsPage() {
  const { t } = useTranslation();
  const [plantId, setPlantId] = useState<string>("");
  const [framework, setFramework] = useState("");
  const [filter, setFilter] = useState<"all" | "red" | "yellow" | "green">("all");
  const [manageOpen, setManageOpen] = useState(false);
  const role = useAuthStore(s => s.user?.role);
  const canManageCatalog = role === "super_admin" || role === "compliance_officer";

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  // Carica solo framework attivi per il plant selezionato
  const { data: activeFrameworks } = useQuery({
    queryKey: ["frameworks", plantId || undefined],
    queryFn: () => controlsApi.frameworks(plantId || undefined),
    retry: false,
  });

  // Quando cambia il plant, aggiorna il framework al primo attivo disponibile
  useEffect(() => {
    if (activeFrameworks && activeFrameworks.length > 0) {
      const codes = activeFrameworks.map(f => f.code);
      if (!codes.includes(framework)) {
        setFramework(codes[0]);
      }
    } else if (activeFrameworks && activeFrameworks.length === 0) {
      setFramework("");
    }
  }, [activeFrameworks]);

  const { data, isLoading } = useQuery({
    queryKey: ["required-docs-status", plantId, framework],
    queryFn: () => scheduleApi.getRequiredDocumentsStatus({
      plant: plantId || undefined,
      framework,
    }),
    // Interroga solo se il framework selezionato è davvero attivo sul plant:
    // durante il cambio sito il framework può restare stantìo un attimo, e non
    // va richiesto un framework non pertinente al plant.
    enabled: !!plantId && !!framework && !!activeFrameworks?.some(f => f.code === framework),
    retry: false,
  });

  const results = data?.results ?? [];
  const filtered = filter === "all" ? results : results.filter(r => r.traffic_light === filter);

  const statusFilterOptions = [
    { value: "all",    labelKey: "schedule.required_docs.status_all" },
    { value: "red",    labelKey: "schedule.required_docs.status_red" },
    { value: "yellow", labelKey: "schedule.required_docs.status_yellow" },
    { value: "green",  labelKey: "schedule.required_docs.status_green" },
  ] as const;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{t("schedule.required_docs.title")}</h2>
        {canManageCatalog && (
          <button
            type="button"
            onClick={() => setManageOpen(true)}
            disabled={!framework}
            title={framework ? "Gestisci il catalogo dei documenti obbligatori del framework selezionato" : "Seleziona prima un framework"}
            className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            ⚙️ Gestisci catalogo
          </button>
        )}
      </div>
      {manageOpen && framework && (
        <CatalogManagerModal framework={framework} onClose={() => setManageOpen(false)} />
      )}

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.required_docs.col_doc").replace("Documento", "Sito")}</label>
            <select
              value={plantId}
              onChange={e => setPlantId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">{t("schedule.required_docs.all_sites")}</option>
              {plants?.map(p => (
                <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Framework</label>
            {activeFrameworks && activeFrameworks.length === 0 ? (
              <p className="text-xs text-amber-600 border border-amber-300 bg-amber-50 rounded px-2 py-1">
                {t("schedule.required_docs.no_framework")}
              </p>
            ) : (
              <div className="flex gap-1 flex-wrap">
                {(activeFrameworks ?? []).map(f => (
                  <button
                    key={f.code}
                    onClick={() => setFramework(f.code)}
                    className={`px-2 py-1 text-xs rounded border ${
                      framework === f.code
                        ? "bg-blue-600 text-white border-blue-600"
                        : "text-gray-600 border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {FRAMEWORK_LABELS[f.code] ?? f.code}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.required_docs.col_status")}</label>
            <div className="flex gap-1">
              {statusFilterOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setFilter(opt.value as typeof filter)}
                  className={`px-2 py-1 text-xs rounded border ${
                    filter === opt.value
                      ? "bg-gray-700 text-white border-gray-700"
                      : "text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {t(opt.labelKey)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      {data && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-xs font-medium text-green-700 uppercase tracking-wide">{t("schedule.required_docs.approved_label")}</p>
            <p className="text-3xl font-bold text-green-700 mt-1">{data.green}</p>
            <p className="text-xs text-green-600 mt-1">{t("schedule.required_docs.total_suffix", { total: data.total })}</p>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-xs font-medium text-yellow-700 uppercase tracking-wide">{t("schedule.required_docs.incomplete_label")}</p>
            <p className="text-3xl font-bold text-yellow-700 mt-1">{data.yellow}</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-xs font-medium text-red-700 uppercase tracking-wide">{t("schedule.required_docs.missing_label")}</p>
            <p className="text-3xl font-bold text-red-700 mt-1">{data.red}</p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {!plantId ? (
          <div className="p-8 text-center text-gray-400 text-sm italic">
            {t("schedule.required_docs.select_plant")}
          </div>
        ) : isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">{t("notification_settings.loading")}</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm italic">
            {results.length === 0
              ? t("schedule.required_docs.no_results_framework")
              : t("schedule.required_docs.no_results_filter")}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_doc")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_type")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_clause")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_present")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((item, idx) => (
                <DocRow key={item.id || `${item.document_type}-${idx}`} item={item} plantId={plantId} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
