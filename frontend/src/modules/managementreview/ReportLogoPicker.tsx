import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { managementReviewApi, reviewErrorMessage, type ManagementReview } from "../../api/endpoints/managementReview";
import { plantsApi } from "../../api/endpoints/plants";
import { AuthenticatedImage } from "../../components/ui/AuthenticatedImage";

// Logo in testa al verbale PDF/HTML, scelto tra i loghi dei siti (società)
// già caricati in Plant Registry. È presentazione e non contenuto del verbale:
// si può cambiare anche dopo l'approvazione.

/** Solo loghi caricati nello storage interno: gli URL esterni non vengono
 *  incorporati nel verbale (stessa regola del backend). */
const hasUploadedLogo = (logoUrl?: string | null) => {
  const v = (logoUrl ?? "").trim();
  return !!v && !v.startsWith("http://") && !v.startsWith("https://");
};

export function ReportLogoPicker({ review, canWrite }: { review: ManagementReview; canWrite: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });
  const withLogo = plants.filter(p => hasUploadedLogo(p.logo_url));

  const save = useMutation({
    mutationFn: (plant: string | null) => managementReviewApi.setReportLogo(review.id, plant),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.report_logo.save_error"))),
  });

  const current = review.report_logo_plant;

  return (
    <div className="mt-4">
      <h4 className="text-sm font-semibold text-gray-700 mb-2">{t("management_review.report_logo.title")}</h4>
      <div className="flex flex-wrap items-center gap-3">
        {canWrite ? (
          <select
            value={current ?? ""}
            disabled={save.isPending}
            onChange={e => save.mutate(e.target.value || null)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">{t("management_review.report_logo.none")}</option>
            {withLogo.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
          </select>
        ) : (
          <span className="text-sm text-gray-800">{review.report_logo_plant_code ?? t("management_review.report_logo.none")}</span>
        )}
        {current && (
          <AuthenticatedImage
            src={`/api/v1/plants/plants/${current}/logo/`}
            alt={t("management_review.report_logo.preview_alt")}
            className="h-10 max-w-[160px] object-contain border border-gray-200 rounded bg-white p-1"
          />
        )}
      </div>
      <p className="text-xs text-gray-400 mt-1">
        {withLogo.length === 0 && canWrite ? t("management_review.report_logo.no_logos") : t("management_review.report_logo.hint")}
      </p>
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}
