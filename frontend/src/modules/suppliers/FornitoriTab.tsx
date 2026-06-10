import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { RiskBadge, Nis2Badge, ConcentrationBadge, EvalDateCell, ExpiryDateCell } from "./supplierBadges";
import { NewSupplierModal, EditSupplierModal } from "./SupplierModals";
import { SendQuestionnaireModal } from "./QuestionnaireModals";
import { ExpandedSupplierRow } from "./ExpandedSupplierRow";
import { useTranslation } from "react-i18next";

export function FornitoriTab() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [newModal, setNewModal] = useState(false);
  const [editModal, setEditModal] = useState<Supplier | null>(null);
  const [sendModal, setSendModal] = useState<Supplier | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterRisk, setFilterRisk] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterNis2, setFilterNis2] = useState("");
  const [search, setSearch] = useState("");
  const [exportLoading, setExportLoading] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suppliers"] }),
    onError: () => window.alert(t("suppliers.list.delete_error")),
  });

  const params: Record<string, string> = {};
  if (filterRisk) params.risk_level = filterRisk;
  if (filterStatus) params.status = filterStatus;
  if (filterNis2) params.nis2_relevant = filterNis2;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", filterRisk, filterStatus, filterNis2],
    queryFn: () => suppliersApi.list(Object.keys(params).length ? params : undefined),
  });
  const allSuppliers = data?.results ?? [];

  // Ordina alfabeticamente per nome (case-insensitive, locale-aware) e
  // applica la ricerca client-side su denominazione + CF/P.IVA + email.
  const suppliers = (() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? allSuppliers.filter(s =>
          (s.name ?? "").toLowerCase().includes(q) ||
          (s.vat_number ?? "").toLowerCase().includes(q) ||
          (s.email ?? "").toLowerCase().includes(q),
        )
      : allSuppliers;
    return [...filtered].sort((a, b) =>
      (a.name ?? "").localeCompare(b.name ?? "", undefined, { sensitivity: "base" }),
    );
  })();

  async function handleExport(nis2Only: boolean) {
    setExportLoading(true);
    try {
      await suppliersApi.exportCsv(nis2Only);
    } catch {
      window.alert(t("suppliers.list.export_error"));
    } finally {
      setExportLoading(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex gap-2 flex-wrap items-center">
          <div className="relative">
            <input
              type="search"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={t("suppliers.list.search_placeholder")}
              className="border rounded pl-8 pr-3 py-1.5 text-sm w-72"
            />
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none">🔍</span>
          </div>
          <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
            <option value="">{t("suppliers.list.all_risks")}</option>
            {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{t(`suppliers.risk.${r}`)}</option>)}
          </select>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
            <option value="">{t("suppliers.list.all_statuses")}</option>
            {["attivo","sospeso","terminato"].map(s => <option key={s} value={s}>{t(`suppliers.list.status_${s}`)}</option>)}
          </select>
          <select value={filterNis2} onChange={e => setFilterNis2(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
            <option value="">{t("suppliers.list.all_nis2")}</option>
            <option value="true">{t("suppliers.list.only_nis2")}</option>
            <option value="false">{t("suppliers.list.not_nis2")}</option>
          </select>
          {search && (
            <span className="text-xs text-gray-500">
              {t("suppliers.list.count_of", { shown: suppliers.length, total: allSuppliers.length })}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {/* Export dropdown */}
          <div className="relative group">
            <button
              disabled={exportLoading}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50 flex items-center gap-1"
            >
              {exportLoading ? t("suppliers.list.exporting") : t("suppliers.list.export_btn")}
            </button>
            <div className="absolute right-0 top-full mt-1 w-52 bg-white border border-gray-200 rounded-lg shadow-lg z-10 hidden group-hover:block">
              <button
                onClick={() => handleExport(false)}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                {t("suppliers.list.export_all")}
              </button>
              <button
                onClick={() => handleExport(true)}
                className="w-full text-left px-4 py-2 text-sm text-purple-700 hover:bg-purple-50 font-medium"
              >
                {t("suppliers.list.export_nis2")}
              </button>
            </div>
          </div>
          <button onClick={() => setNewModal(true)} className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700">
            {t("suppliers.list.new_btn")}
          </button>
        </div>
      </div>

      {newModal && <NewSupplierModal onClose={() => setNewModal(false)} />}
      {editModal && <EditSupplierModal supplier={editModal} onClose={() => setEditModal(null)} />}
      {sendModal && <SendQuestionnaireModal supplier={sendModal} onClose={() => setSendModal(null)} />}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : suppliers.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            {search ? t("suppliers.list.empty_search", { query: search }) : t("suppliers.list.empty")}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_vat")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_country")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">NIS2</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_concentration")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600" title={t("suppliers.list.risk_adj_title")}>{t("suppliers.list.col_risk_adj")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_eval")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.list.col_expiry")}</th>
                <th className="px-4 py-3 w-36"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {suppliers.map(s => (
                <Fragment key={s.id}>
                  <tr data-row-id={s.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-800">
                      <button onClick={() => setExpandedId(expandedId === s.id ? null : s.id)} className="hover:underline text-left">
                        {s.name}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{s.vat_number || <span className="text-red-400 font-sans">{t("suppliers.list.vat_missing")}</span>}</td>
                    <td className="px-4 py-3 text-gray-500">{s.country}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-0.5">
                        <Nis2Badge relevant={s.nis2_relevant} />
                        {s.nis2_relevant && s.nis2_relevance_criterion && (
                          <span className="text-xs text-purple-600">
                            {s.nis2_relevance_criterion === "ict" ? "ICT (a)" : s.nis2_relevance_criterion === "non_fungibile" ? "Non fung. (b)" : "a+b"}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {s.supply_concentration_pct !== null && s.supply_concentration_pct !== undefined
                        ? <div className="flex flex-col gap-0.5">
                            <ConcentrationBadge threshold={s.concentration_threshold} />
                            <span className="text-xs text-gray-400">{s.supply_concentration_pct}%</span>
                          </div>
                        : <span className="text-gray-300">—</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      {s.risk_adj ? (
                        <div className="flex flex-col gap-0.5">
                          <RiskBadge level={s.risk_adj} />
                          {s.internal_risk_level && s.internal_risk_level !== s.risk_adj && (
                            <span className="text-[10px] text-gray-400" title={t("suppliers.list.internal_class_title")}>
                              int: {s.internal_risk_level}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 italic">{t("suppliers.list.not_evaluated")}</span>
                      )}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                    <td className="px-4 py-3"><EvalDateCell date={s.evaluation_date} /></td>
                    <td className="px-4 py-3"><ExpiryDateCell evaluationDate={s.evaluation_date} /></td>
                    <td className="px-4 py-3 text-right space-x-1">
                      <button
                        onClick={() => s.latest_questionnaire_status !== "inviato" && setSendModal(s)}
                        disabled={s.latest_questionnaire_status === "inviato"}
                        title={s.latest_questionnaire_status === "inviato" ? t("suppliers.list.quest_sent_title") : t("suppliers.list.quest_btn_title")}
                        className={`text-xs border rounded px-2 py-1 ${
                          s.latest_questionnaire_status === "inviato"
                            ? "text-gray-400 border-gray-200 bg-gray-50 cursor-not-allowed"
                            : "text-indigo-600 border-indigo-200 hover:bg-indigo-50"
                        }`}
                      >
                        {s.latest_questionnaire_status === "inviato" ? t("suppliers.list.quest_sent") : t("suppliers.list.quest_btn")}
                      </button>
                      <button
                        onClick={() => setEditModal(s)}
                        title={t("suppliers.list.edit_title")}
                        className="text-xs text-gray-600 border border-gray-200 rounded px-2 py-1 hover:bg-gray-50"
                      >
                        {t("actions.edit")}
                      </button>
                      <button
                        onClick={() => { if (window.confirm(t("suppliers.list.delete_confirm", { name: s.name }))) deleteMutation.mutate(s.id); }}
                        disabled={deleteMutation.isPending}
                        title={t("suppliers.list.delete_title")}
                        className="text-xs text-red-600 border border-red-200 rounded px-2 py-1 hover:bg-red-50 disabled:opacity-50"
                      >
                        {t("actions.delete")}
                      </button>
                    </td>
                  </tr>
                  {expandedId === s.id && (
                    <tr>
                      <td colSpan={10} className="bg-gray-50">
                        <ExpandedSupplierRow supplierId={s.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
