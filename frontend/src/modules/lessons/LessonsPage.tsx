import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { lessonsApi, type LessonLearned } from "../../api/endpoints/lessons";
import { StatusBadge } from "../../components/ui/StatusBadge";

function NewLessonModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<LessonLearned>>({});

  const mutation = useMutation({
    mutationFn: lessonsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lessons"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuova lesson learned</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrizione</label>
            <textarea name="description" onChange={handleChange} rows={3} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
              <input name="category" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="es. sicurezza" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito</label>
              <input name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Azione correttiva</label>
            <textarea name="corrective_action" onChange={handleChange} rows={2} className="w-full border rounded px-3 py-2 text-sm" />
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
            {mutation.isPending ? "Salvataggio..." : "Crea lesson"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function LessonsPage() {
  const [showNew, setShowNew] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["lessons"],
    queryFn: () => lessonsApi.list(),
    retry: false,
  });

  const validateMutation = useMutation({
    mutationFn: lessonsApi.validate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lessons"] }),
  });

  const lessons = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Operazioni — Lessons Learned</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuova lesson
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : lessons.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessuna lesson learned registrata</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Categoria</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Sito</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data creazione</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lessons.map(lesson => (
                <tr key={lesson.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{lesson.title}</td>
                  <td className="px-4 py-3 text-gray-600">{lesson.category || "—"}</td>
                  <td className="px-4 py-3"><StatusBadge status={lesson.status} /></td>
                  <td className="px-4 py-3 text-gray-600">{lesson.plant}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(lesson.created_at).toLocaleDateString("it-IT")}</td>
                  <td className="px-4 py-3">
                    {lesson.status === "bozza" && (
                      <button
                        onClick={() => validateMutation.mutate(lesson.id)}
                        disabled={validateMutation.isPending}
                        className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-0.5 hover:bg-blue-50 disabled:opacity-50"
                      >
                        Valida
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewLessonModal onClose={() => setShowNew(false)} />}
    </div>
  );
}
