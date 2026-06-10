import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT, type AssetOT, type RegisterChangeResult } from "../../api/endpoints/assets";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function RegisterChangeForm({
  asset,
  assetType,
  onClose,
}: {
  asset: AssetIT | AssetOT;
  assetType: "IT" | "OT";
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [changeRef, setChangeRef] = useState("");
  const [changeDesc, setChangeDesc] = useState("");
  const [portalUrl, setPortalUrl] = useState("");
  const [result, setResult] = useState<RegisterChangeResult | null>(null);

  const registerMutation = useMutation({
    mutationFn: () =>
      assetsApi.registerChange(asset.id, assetType, {
        change_ref: changeRef,
        change_desc: changeDesc,
        portal_url: portalUrl,
      }),
    onSuccess: (res) => {
      setResult(res);
      qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] });
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => assetsApi.clearRevaluation(asset.id, assetType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] });
      onClose();
    },
  });

  return (
    <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 mt-4">
      {/* Existing change info */}
      {asset.last_change_ref && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-amber-800 text-sm">{t("assets.last_change_registered")}</span>
            {asset.change_portal_url && (
              <a href={asset.change_portal_url} target="_blank" rel="noreferrer" className="text-blue-600 text-sm hover:underline">
                {t("assets.open_ticket")}
              </a>
            )}
          </div>
          <p className="text-sm"><strong>{t("assets.ref_label")}</strong> {asset.last_change_ref}</p>
          <p className="text-sm"><strong>{t("assets.date_label")}</strong> {asset.last_change_date ? new Date(asset.last_change_date).toLocaleDateString(i18n.language || "it") : "—"}</p>
          <p className="text-sm"><strong>{t("assets.description_label")}</strong> {asset.last_change_desc || "—"}</p>
          {asset.needs_revaluation && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-red-600">
                {t("assets.reassessment_since", { date: asset.needs_revaluation_since ? new Date(asset.needs_revaluation_since).toLocaleDateString(i18n.language || "it") : "—" })}
              </span>
              <button
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
                className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
              >
                {t("assets.mark_reassessed")}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Register change form */}
      {result ? (
        <div className="bg-white rounded border border-green-200 p-3">
          <p className="text-sm font-medium text-green-700 mb-1">{t("assets.change_registered_title")}</p>
          <p className="text-xs text-gray-600">{t("assets.ref_label")} {result.ref}</p>
          <p className="text-xs text-gray-600">
            {t("assets.impacted_summary", {
              controls: result.affected.controls,
              risks: result.affected.risks,
              processes: result.affected.processes,
            })}
          </p>
          <button onClick={onClose} className="mt-2 text-xs text-blue-600 hover:underline">{t("common.close")}</button>
        </div>
      ) : (
        <>
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-2">{t("assets.register_change_title")}</p>
          <div className="space-y-2">
            <input
              value={changeRef}
              onChange={(e) => setChangeRef(e.target.value)}
              placeholder={t("assets.change_ticket_placeholder")}
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
            <input
              value={changeDesc}
              onChange={(e) => setChangeDesc(e.target.value)}
              placeholder={t("assets.change_desc_placeholder")}
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
            <input
              value={portalUrl}
              onChange={(e) => setPortalUrl(e.target.value)}
              placeholder={t("assets.change_url_placeholder")}
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
          </div>
          {registerMutation.isError && (
            <p className="text-xs text-red-600 mt-1">{t("assets.register_error")}</p>
          )}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => registerMutation.mutate()}
              disabled={!changeRef || registerMutation.isPending}
              className="px-3 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-50"
            >
              {registerMutation.isPending ? t("assets.registering") : t("assets.register_change_btn")}
            </button>
            <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
