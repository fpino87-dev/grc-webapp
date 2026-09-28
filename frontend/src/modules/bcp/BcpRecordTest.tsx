import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  bcpApi, type BcpPlan, type BcpTestObjective, type BcpTestResult, type BcpTestWarning,
} from "../../api/endpoints/bcp";
import { usePlantToday } from "../../utils/dates";
import { BcpEvidencePicker } from "./BcpEvidencePicker";
import { TEST_TYPES } from "./shared";

export function BcpRecordTest({ plan, onClose }: { plan: BcpPlan; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const today = usePlantToday();
  const [testDate, setTestDate] = useState(today);
  const [testType, setTestType] = useState<string>("tabletop");
  const [result, setResult] = useState<BcpTestResult>("superato");
  const [rtoAchieved, setRtoAchieved] = useState("");
  const [rpoAchieved, setRpoAchieved] = useState("");
  const [participants, setParticipants] = useState("");
  const [notes, setNotes] = useState("");
  const [objectives, setObjectives] = useState<BcpTestObjective[]>([]);
  const [newObjective, setNewObjective] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<BcpTestWarning[]>([]);

  const mutation = useMutation({
    mutationFn: () => {
      const fields: Record<string, string> = {
        plan: plan.id,
        test_date: testDate,
        result,
        test_type: testType,
        objectives: JSON.stringify(objectives),
        notes,
        participants_count: participants || "0",
        evidence_ids: JSON.stringify(evidenceIds),
      };
      if (rtoAchieved) fields.rto_achieved_hours = rtoAchieved;
      if (rpoAchieved) fields.rpo_achieved_hours = rpoAchieved;
      if (!evidenceFile) return bcpApi.recordTest(fields);
      const fd = new FormData();
      Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
      fd.append("evidence_file", evidenceFile);
      return bcpApi.recordTest(fd);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["bcp"] });
      if (res.warnings?.length) setWarnings(res.warnings);
      else onClose();
    },
  });

  function addObjective() {
    const text = newObjective.trim();
    if (!text) return;
    setObjectives(prev => [...prev, { text, met: false }]);
    setNewObjective("");
  }

  if (warnings.length > 0) {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
          <h3 className="text-lg font-semibold mb-3 text-orange-700">{t("bcp.record.warnings_title")}</h3>
          <div className="space-y-2 mb-4">
            {warnings.map((w, i) => (
              <div key={i} className="bg-orange-50 border border-orange-200 rounded p-3 text-sm text-orange-800">
                {t(`bcp.record.warning.${w.code}`, { process: w.process, achieved: w.achieved, target: w.target })}
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mb-4">
            {result === "superato" ? t("bcp.record.pdca_overrun") : t("bcp.record.pdca_failed")}
          </p>
          <div className="flex justify-end">
            <button onClick={onClose} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
              {t("bcp.actions.close")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const errorDetail = (mutation.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-screen overflow-y-auto">
        <h3 className="text-lg font-semibold mb-1">{t("bcp.record.title")}</h3>
        <p className="text-sm text-gray-500 mb-4">{plan.title}</p>

        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.date")} *</label>
              <input type="date" max={today} value={testDate} onChange={e => setTestDate(e.target.value)}
                className="w-full border rounded px-2 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.type")} *</label>
              <select value={testType} onChange={e => setTestType(e.target.value)} className="w-full border rounded px-2 py-2 text-sm">
                {TEST_TYPES.map(v => <option key={v} value={v}>{t(`bcp.test_type.${v}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.result")} *</label>
              <select value={result} onChange={e => setResult(e.target.value as BcpTestResult)} className="w-full border rounded px-2 py-2 text-sm">
                {(["superato", "parziale", "fallito"] as const).map(r => <option key={r} value={r}>{t(`bcp.result.${r}`)}</option>)}
              </select>
            </div>
          </div>
          {result !== "superato" && <p className="text-xs text-orange-700">{t("bcp.record.failed_hint")}</p>}

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.rto_achieved")}</label>
              <input type="number" min="0" value={rtoAchieved} onChange={e => setRtoAchieved(e.target.value)}
                placeholder={plan.rto_hours != null ? t("bcp.record.plan_value", { value: plan.rto_hours }) : "—"}
                className="w-full border rounded px-2 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.rpo_achieved")}</label>
              <input type="number" min="0" value={rpoAchieved} onChange={e => setRpoAchieved(e.target.value)}
                placeholder={plan.rpo_hours != null ? t("bcp.record.plan_value", { value: plan.rpo_hours }) : "—"}
                className="w-full border rounded px-2 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.participants")}</label>
              <input type="number" min="0" value={participants} onChange={e => setParticipants(e.target.value)}
                className="w-full border rounded px-2 py-2 text-sm" />
            </div>
          </div>
          <p className="text-xs text-gray-500">{t("bcp.record.rto_hint")}</p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.objectives")}</label>
            <div className="flex gap-2 mb-2">
              <input
                value={newObjective}
                onChange={e => setNewObjective(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addObjective(); } }}
                placeholder={t("bcp.record.objective_placeholder")}
                className="flex-1 border rounded px-3 py-1.5 text-sm"
              />
              <button onClick={addObjective} className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50">+</button>
            </div>
            {objectives.length > 0 && (
              <>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {objectives.map((o, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={o.met}
                        onChange={() => setObjectives(prev => prev.map((x, i) => (i === idx ? { ...x, met: !x.met } : x)))}
                      />
                      <span className="text-gray-700">{o.text}</span>
                      <button
                        onClick={() => setObjectives(prev => prev.filter((_, i) => i !== idx))}
                        className="ml-auto text-red-400 hover:text-red-600 text-xs"
                        aria-label={t("bcp.actions.remove")}
                      >✕</button>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {t("bcp.record.objectives_met", { met: objectives.filter(o => o.met).length, total: objectives.length })}
                </p>
              </>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.notes")}</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.record.evidence")}</label>
            <BcpEvidencePicker
              plantId={plan.plant}
              file={evidenceFile}
              onFileChange={setEvidenceFile}
              selectedIds={evidenceIds}
              onSelectedChange={setEvidenceIds}
            />
          </div>
        </div>

        {mutation.isError && <p className="text-sm text-red-600 mt-2">{errorDetail ?? t("bcp.form.save_error")}</p>}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("bcp.actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !testDate || testDate > today}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("bcp.actions.saving") : t("bcp.actions.record_test")}
          </button>
        </div>
      </div>
    </div>
  );
}
