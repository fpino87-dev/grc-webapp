import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT } from "../../api/endpoints/assets";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { CriticalityBadge, ChangeBadges } from "./AssetBadges";
import { RegisterChangeForm } from "./RegisterChangeForm";
import { EditAssetModalIT } from "./EditAssetModalIT";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function ITTab({ search }: { search: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editAsset, setEditAsset] = useState<AssetIT | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetsApi.deleteIT(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets-it"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["assets-it"],
    queryFn: () => assetsApi.listIT(),
    retry: false,
  });
  const { data: procData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = procData?.results ?? [];

  const assets: AssetIT[] = (data?.results ?? []).filter((a) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      a.name.toLowerCase().includes(s) ||
      (a.fqdn || "").toLowerCase().includes(s) ||
      (a.service_name || "").toLowerCase().includes(s) ||
      (a.provider || "").toLowerCase().includes(s)
    );
  });

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>;
  }

  return (
    <>
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.fields.name")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.deployment")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">FQDN</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">OS</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.criticality")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.internet_exposed")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.bia_processes")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">EOL</th>
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
              {t("assets.empty_it")}
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <Fragment key={a.id}>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {a.name}
                  <ChangeBadges asset={a} />
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {a.deployment_type === "saas"
                    ? "SaaS"
                    : a.deployment_type === "paas"
                    ? "PaaS"
                    : a.deployment_type === "iaas"
                    ? "IaaS"
                    : "On-prem"}
                  {(a.provider || a.service_name) && (
                    <div className="text-[11px] text-gray-500">
                      {[a.provider, a.service_name].filter(Boolean).join(" — ")}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{a.fqdn}</td>
                <td className="px-4 py-3 text-gray-600">{a.os}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3"><StatusBadge status={a.internet_exposed ? "si" : "no"} /></td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {(() => {
                    const linked = processes.filter((p) => (a.processes || []).includes(p.id));
                    return linked.length ? linked.map((p) => p.name).join(", ") : "—";
                  })()}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {a.eol_date ? new Date(a.eol_date).toLocaleDateString(i18n.language || "it") : "—"}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5"
                  >
                    {expandedId === a.id ? t("common.close") : t("assets.change_btn")}
                  </button>
                  <button
                    onClick={() => setEditAsset(a)}
                    className="ml-2 text-xs text-gray-700 hover:underline border border-gray-200 rounded px-2 py-0.5"
                  >
                    {t("actions.edit")}
                  </button>
                  <button
                    type="button"
                    title={t("assets.actions.delete_title")}
                    onClick={() => {
                      if (!window.confirm(t("assets.actions.delete_confirm", { name: a.name }))) return;
                      deleteMutation.mutate(a.id);
                    }}
                    disabled={deleteMutation.isPending}
                    className="ml-2 text-xs text-red-600 border border-red-200 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                  >
                    🗑
                  </button>
                </td>
              </tr>
              {expandedId === a.id && (
                <tr>
                  <td colSpan={9} className="px-4 pb-4">
                    <RegisterChangeForm asset={a} assetType="IT" onClose={() => setExpandedId(null)} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))
        )}
      </tbody>
    </table>
    {editAsset && <EditAssetModalIT asset={editAsset} onClose={() => setEditAsset(null)} />}
    </>
  );
}
