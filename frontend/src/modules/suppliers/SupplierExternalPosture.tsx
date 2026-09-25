import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { osintApi } from "../../api/endpoints/osint";
import { suppliersApi } from "../../api/endpoints/suppliers";
import { GradeBadge } from "../osint/shared";

/** Postura esterna del fornitore dal modulo OSINT: voto, problemi critici e
 *  storico delle segnalazioni (evidenza di monitoraggio NIS2 art. 21.2.d).
 *  Solo consultazione: la correzione spetta al fornitore. */
export function SupplierExternalPosture({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["osint-supplier-posture", supplierId],
    queryFn: () => osintApi.supplierPosture(supplierId),
    retry: false,
  });
  if (isLoading) return <p className="p-4 text-sm text-gray-400">{t("common.loading")}</p>;
  if (isError) return <p className="p-4 text-sm text-gray-400">{t("suppliers.external.no_access")}</p>;
  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-gray-500">{t("suppliers.external.intro")}</p>
      <ServiceUrlsEditor supplierId={supplierId} />
      {(!data || data.length === 0) && <p className="text-sm text-gray-400">{t("suppliers.external.none")}</p>}
      {(data ?? []).map(d => (
        <div key={d.entity} className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <div className="flex items-center gap-3">
            <GradeBadge grade={d.grade} security={d.security} size="lg" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {d.domain}
                {d.deep_monitoring && (
                  <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700" title={t("osint.chain.deep_hint")}>
                    {t("osint.chain.deep_badge")}
                  </span>
                )}
              </p>
              <p className="text-xs text-gray-500">
                {d.last_scan_at ? t("suppliers.external.last_scan", { date: new Date(d.last_scan_at).toLocaleDateString() }) : t("suppliers.external.never_scanned")}
              </p>
            </div>
            <Link to="/osint" className="text-xs text-primary-700 hover:underline">{t("suppliers.external.open_osint")} →</Link>
          </div>
          {d.critical_open.length === 0 ? (
            <p className="text-xs text-green-700">✓ {t("suppliers.external.no_critical")}</p>
          ) : (
            <ul className="space-y-1">
              {d.critical_open.map(f => (
                <li key={f.id} className="text-xs text-gray-700">
                  🔴 {t(`osint.finding_title.${f.code}`, { defaultValue: f.code })} ·{" "}
                  {f.reported_at
                    ? <span className={f.overdue ? "text-amber-700" : "text-gray-500"}>{t("suppliers.external.reported_on", { date: new Date(f.reported_at).toLocaleDateString() })}</span>
                    : <span className="text-red-700">{t("suppliers.external.not_reported")}</span>}
                </li>
              ))}
            </ul>
          )}
          {d.reports.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-500">{t("suppliers.external.history", { count: d.reports.length })}</summary>
              <ul className="mt-1 space-y-0.5">
                {d.reports.map(r => (
                  <li key={r.id} className="text-gray-600" title={r.note || undefined}>
                    {t(`osint.finding_title.${r.code}`, { defaultValue: r.code })} · {new Date(r.reported_at).toLocaleDateString()}
                    {r.resolved_at ? ` → ✓ ${new Date(r.resolved_at).toLocaleDateString()}` : ""}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}

/** Servizi del fornitore usati dall'azienda (portale ordini, SFTP, VPN…):
 *  solo su questi l'OSINT controlla il certificato. */
function ServiceUrlsEditor({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const { data: supplier } = useQuery({ queryKey: ["supplier", supplierId], queryFn: () => suppliersApi.get(supplierId) });
  const urls = supplier?.service_urls ?? [];
  const save = useMutation({
    mutationFn: (next: string[]) => suppliersApi.update(supplierId, { service_urls: next }),
    onSuccess: () => { setValue(""); setError(""); qc.invalidateQueries({ queryKey: ["supplier", supplierId] }); },
    onError: (e: unknown) => {
      const d = (e as { response?: { data?: { service_urls?: string[] } } })?.response?.data;
      setError(d?.service_urls?.[0] ?? t("common.save_error"));
    },
  });
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-2">
      <p className="text-sm font-medium text-gray-900">{t("suppliers.external.services_title")}</p>
      <p className="text-xs text-gray-500">{t("suppliers.external.services_hint")}</p>
      <div className="flex flex-wrap gap-1.5">
        {urls.map(u => (
          <span key={u} className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
            <span className="font-mono">{u}</span>
            <button onClick={() => save.mutate(urls.filter(x => x !== u))} aria-label={t("suppliers.external.services_remove")}
              className="text-gray-400 hover:text-red-600">×</button>
          </span>
        ))}
        {urls.length === 0 && <span className="text-xs text-gray-400">{t("suppliers.external.services_empty")}</span>}
      </div>
      <div className="flex gap-2">
        <input value={value} onChange={e => setValue(e.target.value)} placeholder="https://portale.fornitore.it"
          aria-label={t("suppliers.external.services_add")} className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
        <button onClick={() => save.mutate([...urls, value.trim()])} disabled={!value.trim() || save.isPending}
          className="px-3 py-1.5 text-sm rounded-lg bg-gray-900 text-white disabled:opacity-50">{t("suppliers.external.services_add")}</button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
