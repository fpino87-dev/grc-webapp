import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetOT } from "../../api/endpoints/assets";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { CriticalityBadge, ChangeBadges } from "./AssetBadges";
import { RegisterChangeForm } from "./RegisterChangeForm";
import { useTranslation } from "react-i18next";

export function OTTab({ search }: { search: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetsApi.deleteOT(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets-ot"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["assets-ot"],
    queryFn: () => assetsApi.listOT(),
    retry: false,
  });
  const { data: procData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = procData?.results ?? [];

  const assets: AssetOT[] = (data?.results ?? []).filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.vendor.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>;
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.fields.name")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.category")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.purdue")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Patchable</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.vendor")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.criticality")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.bia_processes")}</th>
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
              {t("assets.empty_ot")}
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
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {a.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{a.purdue_level}</td>
                <td className="px-4 py-3"><StatusBadge status={a.patchable ? "si" : "no"} /></td>
                <td className="px-4 py-3 text-gray-600">{a.vendor}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {(() => {
                    const linked = processes.filter((p) => (a.processes || []).includes(p.id));
                    return linked.length ? linked.map((p) => p.name).join(", ") : "—";
                  })()}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5"
                  >
                    {expandedId === a.id ? t("common.close") : t("assets.change_btn")}
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
                  <td colSpan={8} className="px-4 pb-4">
                    <RegisterChangeForm asset={a} assetType="OT" onClose={() => setExpandedId(null)} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))
        )}
      </tbody>
    </table>
  );
}
