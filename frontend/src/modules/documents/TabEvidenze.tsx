import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Evidence } from "../../api/endpoints/documents";
import { useAuthStore } from "../../store/auth";
import { evidenceIcon, ExpiryBadge, EVIDENCE_TYPES, expirySort, buildEvidenceGroups } from "./documentUtils";
import { NewEvidenceModal, LinkEvidenceToControlModal } from "./EvidenceModals";
import { useTranslation } from "react-i18next";

type ExpiryFilter = "tutti" | "valide" | "in_scadenza" | "scadute";

export function TabEvidenze() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [typeFilter, setTypeFilter] = useState("");
  const [expiryFilter, setExpiryFilter] = useState<ExpiryFilter>("tutti");
  const [showNew, setShowNew] = useState(false);
  const [filterByPlant, setFilterByPlant] = useState(true);
  const [linkControlsEv, setLinkControlsEv] = useState<Evidence | null>(null);
  const [groupedView, setGroupedView] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  async function handleDownloadEvidence(ev: Evidence) {
    try {
      const blob = await documentsApi.downloadEvidence(ev.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      const filename = ev.file_path ? ev.file_path.split("/").pop() || ev.title || "evidenza" : ev.title || "evidenza";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert(t("documents.errors.evidence_download_failed"));
    }
  }

  const params: Record<string, string> = { page_size: "500" };
  if (typeFilter) params.evidence_type = typeFilter;
  if (expiryFilter !== "tutti") params.expiry = expiryFilter;
  if (filterByPlant && selectedPlant) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["evidences", typeFilter, expiryFilter, filterByPlant, selectedPlant?.id],
    queryFn: () => documentsApi.evidences(params),
    retry: false,
  });

  const deleteEvidenceMutation = useMutation({
    mutationFn: (id: string) => documentsApi.removeEvidence(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidences"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const evidences: Evidence[] = [...(data?.results ?? [])].sort(expirySort);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Filtro scadenza */}
          {(["tutti", "in_scadenza", "valide", "scadute"] as ExpiryFilter[]).map(f => {
            const labels = {
              tutti: t("documents.evidence.filters.all"),
              valide: t("documents.evidence.filters.valid"),
              in_scadenza: t("documents.evidence.filters.expiring"),
              scadute: t("documents.evidence.filters.expired"),
            };
            const colors = { tutti: "", valide: "text-green-700", in_scadenza: "text-orange-700", scadute: "text-red-700" };
            return (
              <button key={f} onClick={() => setExpiryFilter(f)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${expiryFilter === f ? "bg-primary-600 text-white" : `bg-gray-100 hover:bg-gray-200 ${colors[f]}`}`}>
                {labels[f]}
              </button>
            );
          })}

          {/* Filtro tipo */}
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("documents.evidence.filters.all_types")}</option>
              {EVIDENCE_TYPES.map((v) => <option key={v} value={v}>{t(`documents.evidence.types.${v}`)}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setGroupedView(v => !v)}
            className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${groupedView ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
          >
            📁 {groupedView ? t("documents.evidence.toggle_flat") : t("documents.evidence.toggle_grouped")}
          </button>
          {selectedPlant && (
            <label className="flex items-center gap-1 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={filterByPlant}
                onChange={e => setFilterByPlant(e.target.checked)}
                className="rounded"
              />
              <span>{t("documents.filter.only_selected_plant")}</span>
            </label>
          )}
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 shrink-0">
            + {t("documents.evidence.new.submit")}
          </button>
        </div>
      </div>

      {/* Evidence table — flat or grouped */}
      {isLoading ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">{t("common.loading")}</div>
      ) : evidences.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">{t("documents.evidence.empty")}</div>
      ) : groupedView ? (
        /* ── Grouped view ── */
        <div className="space-y-3">
          {buildEvidenceGroups(evidences, t("documents.evidence.group_unassigned")).map(group => {
            const isCollapsed = collapsedGroups.has(group.groupKey);
            return (
              <div key={group.groupKey} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setCollapsedGroups(prev => {
                    const next = new Set(prev);
                    if (next.has(group.groupKey)) next.delete(group.groupKey);
                    else next.add(group.groupKey);
                    return next;
                  })}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                >
                  <span className="text-gray-400">{isCollapsed ? "▶" : "▼"}</span>
                  {group.framework_code && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium shrink-0">{group.framework_code}</span>
                  )}
                  {group.control_external_id && (
                    <span className="text-xs font-mono text-gray-500 shrink-0">{group.control_external_id}</span>
                  )}
                  <span className="text-sm font-medium text-gray-800 flex-1 truncate">{group.control_title}</span>
                  <span className="text-xs bg-green-100 text-green-700 px-1.5 rounded shrink-0">
                    {t("documents.evidence.group_count", { count: group.evidences.length })}
                  </span>
                </button>
                {!isCollapsed && (
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-gray-100">
                      {group.evidences.map(ev => (
                        <tr key={ev.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <span className="text-base">{evidenceIcon(ev.evidence_type)}</span>
                              <span className="text-xs text-gray-500">{t(`documents.evidence.types.${ev.evidence_type}`, { defaultValue: ev.evidence_type })}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 font-medium text-gray-800 max-w-xs">
                            <div className="truncate">{ev.title}</div>
                            {ev.description && <div className="text-xs text-gray-400 truncate">{ev.description}</div>}
                            {(ev.file_url || ev.file_path) && (
                              <button type="button" onClick={() => handleDownloadEvidence(ev)} className="mt-1 inline-flex text-xs text-indigo-600 hover:underline">
                                {t("documents.evidence.actions.download_file")}
                              </button>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center"><ExpiryBadge validUntil={ev.valid_until} /></td>
                          <td className="px-4 py-3 text-gray-600 text-xs">{ev.plant_name || "—"}</td>
                          <td className="px-4 py-3 text-gray-500 text-xs">{ev.uploaded_by_username || "—"}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button onClick={() => setLinkControlsEv(ev)} className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-1.5 py-0.5 hover:border-indigo-400">
                                {t("documents.evidence.actions.link_controls")}
                              </button>
                              <button
                                type="button"
                                title={t("documents.evidence.actions.delete_title")}
                                onClick={() => { if (!window.confirm(t("documents.evidence.actions.delete_confirm", { title: ev.title }))) return; deleteEvidenceMutation.mutate(ev.id); }}
                                disabled={deleteEvidenceMutation.isPending}
                                className="text-xs text-red-600 border border-red-200 rounded px-1.5 py-0.5 hover:bg-red-50 disabled:opacity-50"
                              >🗑</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* ── Flat view ── */
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.type")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.title")}</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.expiry")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.plant")}</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.linked_controls")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.uploaded_by")}</th>
                <th className="px-4 py-3 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {evidences.map(ev => (
                <tr key={ev.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-base">{evidenceIcon(ev.evidence_type)}</span>
                      <span className="text-xs text-gray-500">{t(`documents.evidence.types.${ev.evidence_type}`, { defaultValue: ev.evidence_type })}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-800 max-w-xs">
                    <div className="truncate">{ev.title}</div>
                    {ev.description && <div className="text-xs text-gray-400 truncate">{ev.description}</div>}
                    {(ev.file_url || ev.file_path) && (
                      <button type="button" onClick={() => handleDownloadEvidence(ev)} className="mt-1 inline-flex text-xs text-indigo-600 hover:underline">
                        {t("documents.evidence.actions.download_file")}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center"><ExpiryBadge validUntil={ev.valid_until} /></td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{ev.plant_name || "—"}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${ev.control_instances_count > 0 ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"}`}>
                      {ev.control_instances_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{ev.uploaded_by_username || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button onClick={() => setLinkControlsEv(ev)} className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-1.5 py-0.5 hover:border-indigo-400">
                        {t("documents.evidence.actions.link_controls")}
                      </button>
                      <button
                        type="button"
                        title={t("documents.evidence.actions.delete_title")}
                        onClick={() => { if (!window.confirm(t("documents.evidence.actions.delete_confirm", { title: ev.title }))) return; deleteEvidenceMutation.mutate(ev.id); }}
                        disabled={deleteEvidenceMutation.isPending}
                        className="text-xs text-red-600 border border-red-200 rounded px-1.5 py-0.5 hover:bg-red-50 disabled:opacity-50"
                      >🗑</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && <NewEvidenceModal onClose={() => setShowNew(false)} />}
      {linkControlsEv && <LinkEvidenceToControlModal ev={linkControlsEv} onClose={() => setLinkControlsEv(null)} />}
    </div>
  );
}
