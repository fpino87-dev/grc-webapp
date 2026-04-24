import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { osintApi, type OsintSubdomain, type SubdomainStatus } from "../../api/endpoints/osint";

function StatusBadge({ status }: { status: SubdomainStatus }) {
  const { t } = useTranslation();
  const cls = {
    pending: "bg-yellow-100 text-yellow-800",
    included: "bg-green-100 text-green-800",
    ignored: "bg-gray-100 text-gray-500",
  }[status];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {t(`osint.subdomains.status_${status}`)}
    </span>
  );
}

function SubdomainRow({
  sub,
  onClassify,
  loading,
}: {
  sub: OsintSubdomain;
  onClassify: (id: string, status: SubdomainStatus) => void;
  loading: boolean;
}) {
  const { t } = useTranslation();
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 font-mono text-sm text-gray-800">{sub.subdomain}</td>
      <td className="px-3 py-3 text-xs text-gray-500">{sub.entity_domain}</td>
      <td className="px-3 py-3">
        <StatusBadge status={sub.status} />
      </td>
      <td className="px-3 py-3 text-xs text-gray-400">
        {new Date(sub.first_seen).toLocaleDateString("it-IT")}
      </td>
      <td className="px-3 py-3">
        <div className="flex gap-1">
          {sub.status !== "included" && (
            <button
              onClick={() => onClassify(sub.id, "included")}
              disabled={loading}
              className="px-2 py-1 text-xs border rounded text-green-700 border-green-300 hover:bg-green-50 disabled:opacity-50"
            >
              {t("osint.subdomains.include")}
            </button>
          )}
          {sub.status !== "ignored" && (
            <button
              onClick={() => onClassify(sub.id, "ignored")}
              disabled={loading}
              className="px-2 py-1 text-xs border rounded text-gray-500 hover:bg-gray-50 disabled:opacity-50"
            >
              {t("osint.subdomains.ignore")}
            </button>
          )}
          {sub.status !== "pending" && (
            <button
              onClick={() => onClassify(sub.id, "pending")}
              disabled={loading}
              className="px-2 py-1 text-xs border rounded text-yellow-700 border-yellow-300 hover:bg-yellow-50 disabled:opacity-50"
            >
              {t("osint.subdomains.reset")}
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

export function OsintSubdomainsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"pending" | "all">("pending");

  const { data: pendingSubdomains = [], isLoading: pendingLoading } = useQuery({
    queryKey: ["osint-subdomains-page", "pending"],
    queryFn: () => osintApi.subdomains("pending"),
  });

  const { data: allSubdomains = [], isLoading: allLoading } = useQuery({
    queryKey: ["osint-subdomains-page", "all"],
    queryFn: () => osintApi.subdomains(),
  });

  const subdomains = tab === "pending" ? pendingSubdomains : allSubdomains;
  const isLoading = tab === "pending" ? pendingLoading : allLoading;

  const classifyMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: SubdomainStatus }) =>
      osintApi.classifySubdomain(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-subdomains-page"] });
      qc.invalidateQueries({ queryKey: ["osint-subdomains-pending"] });
      qc.invalidateQueries({ queryKey: ["osint-summary"] });
    },
  });

  const classifiedCount = allSubdomains.filter(s => s.status !== "pending").length;

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link to="/osint" className="text-sm text-gray-500 hover:text-gray-700">← {t("osint.title")}</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold text-gray-900">{t("osint.subdomains.title")}</h1>
      </div>

      <p className="text-sm text-gray-500">{t("osint.subdomains.subtitle")}</p>

      {/* Tab */}
      <div className="flex gap-2">
        <button
          onClick={() => setTab("pending")}
          className={`px-4 py-1.5 text-sm rounded-full border ${tab === "pending" ? "bg-yellow-500 text-white border-yellow-500" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
        >
          {t("osint.subdomains.tab_pending")}
          {pendingSubdomains.length > 0 && (
            <span className="ml-1.5 bg-yellow-600 text-white text-xs rounded-full px-1.5">{pendingSubdomains.length}</span>
          )}
        </button>
        <button
          onClick={() => setTab("all")}
          className={`px-4 py-1.5 text-sm rounded-full border ${tab === "all" ? "bg-primary-600 text-white border-primary-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
        >
          {t("osint.subdomains.tab_all")}
          {allSubdomains.length > 0 && (
            <span className={`ml-1.5 text-xs rounded-full px-1.5 ${tab === "all" ? "bg-primary-700 text-white" : "bg-gray-200 text-gray-600"}`}>
              {allSubdomains.length}
            </span>
          )}
        </button>
      </div>

      {isLoading && <div className="text-gray-400 text-sm">{t("common.loading")}</div>}

      {/* Empty state: pending tab con 0 pending ma classificati esistenti */}
      {!isLoading && tab === "pending" && pendingSubdomains.length === 0 && (
        <div className="border rounded-xl p-8 text-center bg-white">
          <p className="text-2xl mb-2">✅</p>
          <p className="text-gray-500 text-sm">{t("osint.subdomains.all_classified")}</p>
          {classifiedCount > 0 && (
            <p className="text-xs text-gray-400 mt-2">
              {t("osint.subdomains.classified_hint", { count: classifiedCount })}
              {" "}
              <button
                onClick={() => setTab("all")}
                className="text-primary-600 hover:underline font-medium"
              >
                {t("osint.subdomains.tab_all")} →
              </button>
            </p>
          )}
        </div>
      )}

      {/* Empty state: all tab vuoto */}
      {!isLoading && tab === "all" && allSubdomains.length === 0 && (
        <div className="border rounded-xl p-8 text-center bg-white">
          <p className="text-2xl mb-2">📭</p>
          <p className="text-gray-500 text-sm">{t("osint.subdomains.all_classified")}</p>
        </div>
      )}

      {subdomains.length > 0 && (
        <div className="border rounded-xl overflow-hidden bg-white">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.subdomains.col_subdomain")}</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.subdomains.col_entity")}</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.subdomains.col_status")}</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.subdomains.col_first_seen")}</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {subdomains.map(sub => (
                <SubdomainRow
                  key={sub.id}
                  sub={sub}
                  onClassify={(id, status) => classifyMutation.mutate({ id, status })}
                  loading={classifyMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
