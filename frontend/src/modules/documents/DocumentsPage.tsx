import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document } from "../../api/endpoints/documents";
import { StatusBadge } from "../../components/ui/StatusBadge";

type StatusFilter = "tutti" | "bozza" | "revisione" | "approvazione" | "approvato";

const STATUS_FILTERS: { label: string; value: StatusFilter }[] = [
  { label: "Tutti", value: "tutti" },
  { label: "Bozza", value: "bozza" },
  { label: "In revisione", value: "revisione" },
  { label: "In approvazione", value: "approvazione" },
  { label: "Approvati", value: "approvato" },
];

function NewDocumentModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Document>>({ is_mandatory: false });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: documentsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["documents"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || "Errore durante il salvataggio"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const value = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo documento</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Categoria *</label>
            <select name="category" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— seleziona —</option>
              <option value="policy">Policy</option>
              <option value="procedura">Procedura</option>
              <option value="istruzione">Istruzione operativa</option>
              <option value="registro">Registro</option>
              <option value="piano">Piano</option>
              <option value="evidence">Evidenza</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Scadenza revisione</label>
            <input type="date" name="review_due_date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_mandatory" name="is_mandatory" onChange={handleChange} className="rounded" />
            <label htmlFor="is_mandatory" className="text-sm text-gray-700">Documento obbligatorio</label>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.title || !form.category}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea documento"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function DocumentsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("tutti");
  const [showNew, setShowNew] = useState(false);
  const qc = useQueryClient();

  const params: Record<string, string> = {};
  if (statusFilter !== "tutti") params.status = statusFilter;

  const { data, isLoading } = useQuery({
    queryKey: ["documents", statusFilter],
    queryFn: () => documentsApi.list(params),
    retry: false,
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) => documentsApi.submit(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => documentsApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => documentsApi.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  const documents: Document[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Documenti</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo documento
        </button>
      </div>

      <div className="mb-4 flex items-center gap-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-primary-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun documento trovato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Categoria</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Obbligatorio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scadenza revisione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Approvato il</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{doc.title}</td>
                  <td className="px-4 py-3 text-gray-600">{doc.category}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3">
                    {doc.is_mandatory ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                        Obbligatorio
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
                        Facoltativo
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {doc.review_due_date
                      ? new Date(doc.review_due_date).toLocaleDateString("it-IT")
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {doc.approved_at
                      ? new Date(doc.approved_at).toLocaleDateString("it-IT")
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {doc.status === "bozza" && (
                        <button
                          onClick={() => submitMutation.mutate(doc.id)}
                          disabled={submitMutation.isPending}
                          className="text-xs text-gray-500 hover:text-blue-700 border border-gray-300 rounded px-2 py-0.5 hover:border-blue-400 disabled:opacity-50 whitespace-nowrap"
                        >
                          Invia per revisione
                        </button>
                      )}
                      {doc.status === "revisione" && (
                        <>
                          <button
                            onClick={() => approveMutation.mutate(doc.id)}
                            disabled={approveMutation.isPending}
                            className="text-xs text-gray-500 hover:text-green-700 border border-gray-300 rounded px-2 py-0.5 hover:border-green-400 disabled:opacity-50"
                          >
                            Approva
                          </button>
                          <button
                            onClick={() => rejectMutation.mutate(doc.id)}
                            disabled={rejectMutation.isPending}
                            className="text-xs text-gray-500 hover:text-red-700 border border-gray-300 rounded px-2 py-0.5 hover:border-red-400 disabled:opacity-50"
                          >
                            Rifiuta
                          </button>
                        </>
                      )}
                      {doc.status === "approvazione" && (
                        <>
                          <button
                            onClick={() => approveMutation.mutate(doc.id)}
                            disabled={approveMutation.isPending}
                            className="text-xs text-gray-500 hover:text-green-700 border border-gray-300 rounded px-2 py-0.5 hover:border-green-400 disabled:opacity-50"
                          >
                            Approva
                          </button>
                          <button
                            onClick={() => rejectMutation.mutate(doc.id)}
                            disabled={rejectMutation.isPending}
                            className="text-xs text-gray-500 hover:text-red-700 border border-gray-300 rounded px-2 py-0.5 hover:border-red-400 disabled:opacity-50"
                          >
                            Rifiuta
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewDocumentModal onClose={() => setShowNew(false)} />}
    </div>
  );
}
