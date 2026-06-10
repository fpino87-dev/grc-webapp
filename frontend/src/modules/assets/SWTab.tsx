import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetSW } from "../../api/endpoints/assets";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { CriticalityBadge, EosBadge, APPROVAL_STATUS_COLORS } from "./AssetBadges";
import { EditAssetModalSW } from "./AssetSwModals";
import { useTranslation } from "react-i18next";

export function SWTab({ search }: { search: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editAsset, setEditAsset] = useState<AssetSW | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetsApi.deleteSW(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets-sw"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["assets-sw"],
    queryFn: () => assetsApi.listSW(),
    retry: false,
  });
  const { data: procData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = procData?.results ?? [];

  const assets: AssetSW[] = (data?.results ?? []).filter(a =>
    !search || a.name.toLowerCase().includes(search.toLowerCase()) || (a.vendor || "").toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>;

  return (
    <>
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.fields.name")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.vendor")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.sw.version_label")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.sw.approval_status_label")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.sw.license_type_label")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.sw.eos_label")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("eval_assistant.bia.columns.level")}</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.bia_processes_label")}</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {assets.length === 0 ? (
            <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">{t("assets.sw.empty")}</td></tr>
          ) : assets.map(a => (
            <tr key={a.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-medium text-gray-800">{a.name}</td>
              <td className="px-4 py-3 text-gray-600">{a.vendor || "—"}</td>
              <td className="px-4 py-3 text-gray-500 font-mono text-xs">{a.version || "—"}</td>
              <td className="px-4 py-3">
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${APPROVAL_STATUS_COLORS[a.approval_status] ?? "bg-gray-100 text-gray-600"}`}>
                  {t(`assets.sw.status_${a.approval_status}`)}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">{a.license_type ? t(`assets.sw.license_${a.license_type}`) : "—"}</td>
              <td className="px-4 py-3"><EosBadge asset={a} /></td>
              <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
              <td className="px-4 py-3 text-gray-600 text-xs">
                {(() => {
                  const linked = processes.filter(p => (a.processes || []).includes(p.id));
                  return linked.length ? linked.map(p => p.name).join(", ") : "—";
                })()}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <button onClick={() => setEditAsset(a)} className="text-xs text-gray-700 hover:underline border border-gray-200 rounded px-2 py-0.5">
                  {t("actions.edit")}
                </button>
                <button
                  type="button"
                  title={t("assets.actions.delete_title")}
                  onClick={() => { if (!window.confirm(t("assets.actions.delete_confirm", { name: a.name }))) return; deleteMutation.mutate(a.id); }}
                  disabled={deleteMutation.isPending}
                  className="ml-2 text-xs text-red-600 border border-red-200 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                >
                  🗑
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editAsset && <EditAssetModalSW asset={editAsset} onClose={() => setEditAsset(null)} />}
    </>
  );
}
