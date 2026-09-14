import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type SupplierQuestionnaire } from "../../api/endpoints/suppliers";
import { QStatus, RiskBadge } from "./supplierBadges";
import { EvaluateModal, RegisterExistingEvaluationModal } from "./QuestionnaireModals";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { addDaysISO, usePlantToday } from "../../utils/dates";

type Bucket = "waiting" | "valid" | "expiring" | "expired";

// Stato "operativo" del questionario per riepilogo e filtro. La scadenza della
// valutazione vive in `expires_at` (lo stato "scaduto" non viene impostato da
// nessun processo), quindi una valutazione oltre la validità conta come scaduta.
function bucketOf(q: SupplierQuestionnaire, today: string, in90: string): Bucket {
  if (q.status === "inviato") return "waiting";
  if (q.status === "scaduto" || (q.expires_at && q.expires_at < today)) return "expired";
  if (q.expires_at && q.expires_at <= in90) return "expiring";
  return "valid";
}

const CARD_STYLES: Record<Bucket, { border: string; ring: string; text: string }> = {
  valid:    { border: "border-green-300",  ring: "ring-green-400",  text: "text-green-600" },
  expiring: { border: "border-yellow-300", ring: "ring-yellow-400", text: "text-yellow-600" },
  waiting:  { border: "border-blue-300",   ring: "ring-blue-400",   text: "text-blue-600" },
  expired:  { border: "border-red-300",    ring: "ring-red-400",    text: "text-red-600" },
};

export function QuestionariTab() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const today = usePlantToday();
  const in90 = addDaysISO(today, 90);
  const [evaluateTarget, setEvaluateTarget] = useState<SupplierQuestionnaire | null>(null);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [filterBucket, setFilterBucket] = useState<Bucket | "">("");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-questionnaires"],
    queryFn: () => suppliersApi.listQuestionnaires(),
  });
  const allQuestionnaires = data ?? [];

  const counts: Record<Bucket, number> = { waiting: 0, valid: 0, expiring: 0, expired: 0 };
  let thirdSend = 0;
  for (const q of allQuestionnaires) {
    const b = bucketOf(q, today, in90);
    counts[b] += 1;
    if (b === "waiting" && q.send_count >= 3) thirdSend += 1;
  }

  const term = search.trim().toLowerCase();
  const questionnaires = allQuestionnaires.filter(q =>
    (!filterBucket || bucketOf(q, today, in90) === filterBucket) &&
    (!term ||
      (q.supplier_name ?? "").toLowerCase().includes(term) ||
      (q.sent_to ?? "").toLowerCase().includes(term)),
  );
  const isFiltered = !!filterBucket || !!term;

  const resendMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.resendQuestionnaire(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] }),
    onError: (e: any) => window.alert(e?.response?.data?.error || t("suppliers.quests.error_resend")),
  });

  function card(bucket: Bucket, label: string, hint?: string) {
    const style = CARD_STYLES[bucket];
    const active = filterBucket === bucket;
    return (
      <button
        type="button"
        onClick={() => setFilterBucket(active ? "" : bucket)}
        title={t("suppliers.quests.card_filter_title")}
        aria-pressed={active}
        className={`text-left bg-white border ${style.border} rounded-lg p-4 hover:shadow-sm transition ${active ? `ring-2 ${style.ring}` : ""}`}
      >
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className={`text-3xl font-bold ${style.text} mt-1`}>{counts[bucket]}</p>
        {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
      </button>
    );
  }

  return (
    <div>
      {evaluateTarget && <EvaluateModal questionnaire={evaluateTarget} onClose={() => setEvaluateTarget(null)} />}
      {registerOpen && <RegisterExistingEvaluationModal onClose={() => setRegisterOpen(false)} />}

      {!isLoading && allQuestionnaires.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {card("valid", t("suppliers.quests.kpi_valid"))}
          {card("expiring", t("suppliers.quests.kpi_expiring"))}
          {card("waiting", t("suppliers.quests.kpi_waiting"), thirdSend > 0 ? t("suppliers.quests.kpi_waiting_third", { n: thirdSend }) : undefined)}
          {card("expired", t("suppliers.quests.kpi_expired"))}
        </div>
      )}

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative">
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={t("suppliers.quests.search_placeholder")}
            className="border rounded pl-8 pr-3 py-1.5 text-sm w-64"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none">🔍</span>
        </div>
        <select value={filterBucket} onChange={e => setFilterBucket(e.target.value as Bucket | "")} className="border rounded px-3 py-1.5 text-sm">
          <option value="">{t("suppliers.quests.all_statuses")}</option>
          <option value="waiting">{t("suppliers.quests.waiting")}</option>
          <option value="valid">{t("suppliers.quests.filter_valid")}</option>
          <option value="expiring">{t("suppliers.quests.filter_expiring")}</option>
          <option value="expired">{t("suppliers.quests.expired")}</option>
        </select>
        <span className="text-sm text-gray-500">
          {isFiltered
            ? t("suppliers.list.count_of", { shown: questionnaires.length, total: allQuestionnaires.length })
            : t("suppliers.quests.count", { count: allQuestionnaires.length })}
        </span>
        <button
          onClick={() => setRegisterOpen(true)}
          title={t("suppliers.register_existing.intro")}
          className="ml-auto text-sm text-green-700 border border-green-200 rounded px-3 py-1.5 hover:bg-green-50"
        >
          {t("suppliers.register_existing.btn")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-center text-gray-400">{t("common.loading")}</div>
        ) : allQuestionnaires.length === 0 ? (
          <div className="p-6 text-center text-gray-400">{t("suppliers.quests.none")}</div>
        ) : questionnaires.length === 0 ? (
          <div className="p-6 text-center text-gray-400">{t("suppliers.quests.no_match")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_supplier")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_sent_to")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_first_send")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_last_send")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_eval_date")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_result")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_expires")}</th>
                <th className="px-4 py-3 w-28"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {questionnaires.map(q => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{q.supplier_name}</td>
                  {q.origin === "esistente" ? (
                    <>
                      <td colSpan={3} className="px-4 py-3 text-xs text-gray-400 italic">{t("suppliers.quests.origin_existing_title")}</td>
                      <td className="px-4 py-3">
                        <span title={q.notes || undefined} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 cursor-help">
                          {t("suppliers.quests.origin_existing")}
                        </span>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-4 py-3 text-gray-500 text-xs">{q.sent_to}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{new Date(q.sent_at).toLocaleDateString(i18n.language || "it")}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{new Date(q.last_sent_at).toLocaleDateString(i18n.language || "it")}</td>
                      <td className="px-4 py-3"><QStatus status={q.status} sendCount={q.send_count} /></td>
                    </>
                  )}
                  <td className="px-4 py-3 text-gray-600">{q.evaluation_date ? new Date(q.evaluation_date).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3">{q.risk_result ? <RiskBadge level={q.risk_result} /> : <span className="text-gray-400">—</span>}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{q.expires_at ? new Date(q.expires_at).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3 text-right space-x-1">
                    {q.status === "inviato" && (
                      <>
                        <button
                          onClick={() => resendMutation.mutate(q.id)}
                          disabled={resendMutation.isPending}
                          className="text-xs text-indigo-600 border border-indigo-200 rounded px-1.5 py-0.5 hover:bg-indigo-50 disabled:opacity-50"
                          title={q.send_count >= 3 ? t("suppliers.quests.resend_max_title") : t("suppliers.quests.resend_title", { n: q.send_count + 1 })}
                        >
                          {t("suppliers.quests.resend")} {q.send_count >= 3 ? "(3°)" : ""}
                        </button>
                        <button
                          onClick={() => setEvaluateTarget(q)}
                          className="text-xs text-green-600 border border-green-200 rounded px-1.5 py-0.5 hover:bg-green-50"
                        >
                          {t("suppliers.quests.evaluate")}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
