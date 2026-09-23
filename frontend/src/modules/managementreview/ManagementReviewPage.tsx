import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { managementReviewApi, reviewErrorMessage, type ManagementReview, type ReviewKind } from "../../api/endpoints/managementReview";
import { governanceApi } from "../../api/endpoints/governance";
import { plantsApi } from "../../api/endpoints/plants";
import { usersApi, type GrcUser } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { ReviewDetail } from "./ReviewDetail";
import { bodiesForScope } from "./ParticipantsSection";

const APPROVAL_COLORS: Record<string, string> = {
  bozza:     "bg-gray-100 text-gray-600",
  in_review: "bg-blue-100 text-blue-700",
  approvato: "bg-green-100 text-green-700",
  rifiutato: "bg-red-100 text-red-700",
};

// ── NewReviewModal ────────────────────────────────────────────────────────────

function NewReviewModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<ManagementReview>>({ kind: "completo" });
  // undefined = scelta automatica (il CdA se c'è, altrimenti il primo organo
  // ammesso per il perimetro); null = nessun organo, scelto esplicitamente.
  const [bodyChoice, setBodyChoice] = useState<string | null | undefined>(undefined);
  const [error, setError] = useState("");

  const { data: bodies = [] } = useQuery({
    queryKey: ["committees"],
    queryFn: () => governanceApi.committees(),
    retry: false,
  });
  const plantId = (form.plant as string | null | undefined) ?? null;
  const eligible = bodiesForScope(bodies, plantId);
  const auto = eligible.find(b => b.committee_type === "cda") ?? eligible[0] ?? null;
  const bodyId = bodyChoice === undefined
    ? auto?.id ?? null
    : eligible.some(b => b.id === bodyChoice) ? bodyChoice : null;
  const selectedBody = eligible.find(b => b.id === bodyId) ?? null;

  const mutation = useMutation({
    mutationFn: managementReviewApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); onClose(); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.new.save_error"))),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value || null }));
  }

  const activeMembers = selectedBody?.members.filter(m => m.is_active) ?? [];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("management_review.new.title")}</h3>
        <div className="space-y-3">
          <fieldset>
            <legend className="block text-sm font-medium text-gray-700 mb-1">{t("management_review.targeted.kind_label")}</legend>
            <div className="space-y-1">
              {(["completo", "mirato"] as ReviewKind[]).map(k => (
                <label key={k} className={`flex items-start gap-2 border rounded px-3 py-2 cursor-pointer ${form.kind === k ? "border-primary-400 bg-primary-50/40" : "border-gray-200"}`}>
                  <input type="radio" name="kind" className="mt-1" checked={form.kind === k}
                         onChange={() => setForm(prev => ({ ...prev, kind: k }))} />
                  <span>
                    <span className="block text-sm text-gray-800">{t(`management_review.targeted.kinds.${k}`)}</span>
                    <span className="block text-xs text-gray-500">{t(`management_review.targeted.kind_hints.${k}`)}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("management_review.new.title_label")}</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("management_review.new.title_ph")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("management_review.new.plant_label")}</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("management_review.new.org_wide_opt")}</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("management_review.new.date_label")}</label>
            <input type="date" name="review_date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("management_review.participants.body")}</label>
            <select
              value={bodyId ?? ""}
              onChange={e => setBodyChoice(e.target.value || null)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">{t("management_review.participants.no_body")}</option>
              {eligible.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {selectedBody
                ? t("management_review.new.body_hint", { n: activeMembers.length })
                : t("management_review.new.no_body_hint")}
            </p>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("management_review.new.cancel")}</button>
          <button
            onClick={() => mutation.mutate({ ...form, governing_body: bodyId })}
            disabled={mutation.isPending || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("management_review.new.saving") : t("management_review.new.create")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ManagementReviewPage ──────────────────────────────────────────────────────

export function ManagementReviewPage() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [users, setUsers] = useState<GrcUser[]>([]);
  const [kindFilter, setKindFilter] = useState<"" | ReviewKind>("");
  const qc = useQueryClient();

  const selectedPlant = useAuthStore(s => s.selectedPlant);
  // Creare ed eliminare riesami è governance; un componente dell'organo con
  // account li consulta e li approva dal dettaglio.
  const role = useAuthStore(s => s.user?.role) ?? "";
  const isGovernance = ["super_admin", "compliance_officer"].includes(role);

  useEffect(() => {
    usersApi.list().then(setUsers).catch(() => {});
  }, []);

  const params: Record<string, string> = {};
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["management-review", selectedPlant?.id],
    queryFn: () => managementReviewApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => managementReviewApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["management-review"] });
      setConfirmDelete(null);
      if (selectedId === confirmDelete) setSelectedId(null);
    },
  });

  const reviews = (data?.results ?? []).filter(r => !kindFilter || r.kind === kindFilter);
  const selected = reviews.find(r => r.id === selectedId) ?? null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-1">
          {t("management_review.list.h2")}
          <ModuleHelp
            title={t("management_review.help.title")}
            description={t("management_review.help.description")}
            steps={[
              t("management_review.help.steps.1"),
              t("management_review.help.steps.2"),
              t("management_review.help.steps.3"),
              t("management_review.help.steps.4"),
              t("management_review.help.steps.5"),
              t("management_review.help.steps.6"),
              t("management_review.help.steps.7"),
              t("management_review.help.steps.8"),
              t("management_review.help.steps.9"),
              t("management_review.help.steps.10"),
            ]}
            connections={[
              { module: "M06 Risk", relation: t("management_review.help.connections.risk") },
              { module: "M09 Incidenti", relation: t("management_review.help.connections.incidents") },
              { module: "M11 PDCA", relation: t("management_review.help.connections.pdca") },
              { module: "M08 Task", relation: t("management_review.help.connections.tasks") },
              { module: "M17 Audit", relation: t("management_review.help.connections.audit") },
              { module: "M20 AI", relation: t("management_review.help.connections.ai") },
            ]}
            configNeeded={[t("management_review.help.config_needed.1")]}
          />
        </h2>
        {isGovernance && (
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
            + {t("management_review.list.new")}
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        {selectedPlant ? (
          <p className="text-xs text-gray-500">
            {t("management_review.list.filter_active")} <span className="font-medium text-gray-700">{selectedPlant.name}</span>
          </p>
        ) : <span />}
        <select value={kindFilter} onChange={e => setKindFilter(e.target.value as "" | ReviewKind)}
                className="border rounded px-2 py-1 text-xs" aria-label={t("management_review.targeted.kind_label")}>
          <option value="">{t("management_review.targeted.filter_all")}</option>
          <option value="completo">{t("management_review.targeted.kinds.completo")}</option>
          <option value="mirato">{t("management_review.targeted.kinds.mirato")}</option>
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("management_review.list.loading")}</div>
        ) : reviews.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">{t("management_review.list.none")}</p>
            {isGovernance && (
              <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">{t("management_review.list.create_first")}</button>
            )}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_plant")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_approval")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_snapshot")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_actions")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("management_review.list.col_date")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reviews.map(r => (
                <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {r.title}
                    {r.kind === "mirato" && (
                      <span className="ml-2 text-xs font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">
                        {t("management_review.targeted.badge")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.plant_name ?? <span className="text-gray-300">{t("management_review.list.org_wide")}</span>}</td>
                  <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${APPROVAL_COLORS[r.approval_status] ?? "bg-gray-100 text-gray-600"}`}>
                      {t(`management_review.approval.${r.approval_status}`, r.approval_status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {r.snapshot_generated_at
                      ? <span className="text-green-600">✓ {new Date(r.snapshot_generated_at).toLocaleDateString(i18n.language || "it")}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {r.actions.length > 0
                      ? <span>{t("management_review.list.actions_open", { open: r.actions.filter(a => a.status === "aperto").length, total: r.actions.length })}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.review_date}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => setSelectedId(r.id)} className="text-xs text-primary-600 hover:underline">{t("management_review.list.detail")}</button>
                      {!isGovernance ? null : confirmDelete === r.id ? (
                        <span className="flex items-center gap-1">
                          <button
                            onClick={() => deleteMutation.mutate(r.id)}
                            disabled={deleteMutation.isPending}
                            className="text-xs text-white bg-red-600 hover:bg-red-700 px-2 py-0.5 rounded disabled:opacity-50"
                          >
                            {t("management_review.list.confirm")}
                          </button>
                          <button onClick={() => setConfirmDelete(null)} className="text-xs text-gray-500 hover:underline">{t("management_review.list.cancel")}</button>
                        </span>
                      ) : (
                        <button
                          onClick={() => setConfirmDelete(r.id)}
                          className="text-xs text-red-500 hover:text-red-700 hover:underline"
                        >
                          {t("management_review.list.delete")}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewReviewModal plants={plants} onClose={() => setShowNew(false)} />}
      {selected && <ReviewDetail review={selected} users={users} plants={plants ?? []} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
