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

  const { data: subdomains = [], isLoading } = useQuery({
    queryKey: ["osint-subdomains-all"],
    queryFn: () => osintApi.entities().then(() => osintApi.pendingSubdomains()),
  });

  const { data: allSubdomains = [] } = useQuery({
    queryKey: ["osint-subdomains-all-list"],
    queryFn: async () => {
      const entities = await osintApi.entities();
      const results: OsintSubdomain[] = [];
      for (const e of entities.slice(0, 20)) {
        try {
          const detail = await osintApi.entity(e.id);
          if (detail.pending_subdomains_count > 0) {
            const pending = await osintApi.pendingSubdomains();
            results.push(...pending);
            break;
          }
        } catch { /* ignore */ }
      }
      return results;
    },
  });

  const classifyMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: SubdomainStatus }) =>
      osintApi.classifySubdomain(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-subdomains-pending"] });
      qc.invalidateQueries({ queryKey: ["osint-subdomains-all"] });
      qc.invalidateQueries({ queryKey: ["osint-subdomains-all-list"] });
    },
  });

  const pending = subdomains.filter(s => s.status === "pending");
  const processed = [...subdomains, ...allSubdomains.filter(
    s => !subdomains.find(x => x.id === s.id)
  )].filter(s => s.status !== "pending");

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link to="/osint" className="text-sm text-gray-500 hover:text-gray-700">← {t("osint.title")}</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold text-gray-900">{t("osint.subdomains.title")}</h1>
      </div>

      <p className="text-sm text-gray-500">{t("osint.subdomains.subtitle")}</p>

      {isLoading && <div className="text-gray-400 text-sm">{t("common.loading")}</div>}

      {/* Pending */}
      {pending.length > 0 && (
        <div className="border rounded-xl overflow-hidden bg-white">
          <div className="px-4 py-3 border-b bg-yellow-50 flex items-center gap-2">
            <span>⚠️</span>
            <h2 className="font-semibold text-yellow-800 text-sm">
              {t("osint.subdomains.pending_count", { count: pending.length })}
            </h2>
          </div>
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
              {pending.map(sub => (
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

      {!isLoading && pending.length === 0 && (
        <div className="border rounded-xl p-8 text-center bg-white">
          <p className="text-2xl mb-2">✅</p>
          <p className="text-gray-500 text-sm">{t("osint.subdomains.all_classified")}</p>
        </div>
      )}
    </div>
  );
}
