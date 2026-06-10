import { useState } from "react";
import { InternalEvaluationSection } from "./InternalEvaluationSection";
import { AssessmentsTable } from "./AssessmentsTable";
import { NdaSection } from "./NdaSection";
import { useTranslation } from "react-i18next";

export function ExpandedSupplierRow({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const [subTab, setSubTab] = useState<"internal" | "assessments" | "nda">("internal");
  return (
    <div>
      <div className="flex border-b border-gray-200 px-4 pt-2">
        <button
          onClick={() => setSubTab("internal")}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ${subTab === "internal" ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          {t("suppliers.subtabs.internal")}
        </button>
        <button
          onClick={() => setSubTab("assessments")}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ${subTab === "assessments" ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          {t("suppliers.subtabs.assessments")}
        </button>
        <button
          onClick={() => setSubTab("nda")}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ${subTab === "nda" ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          {t("suppliers.subtabs.nda")}
        </button>
      </div>
      {subTab === "internal" && <InternalEvaluationSection supplierId={supplierId} />}
      {subTab === "assessments" && <AssessmentsTable supplierId={supplierId} />}
      {subTab === "nda" && <NdaSection supplierId={supplierId} />}
    </div>
  );
}
