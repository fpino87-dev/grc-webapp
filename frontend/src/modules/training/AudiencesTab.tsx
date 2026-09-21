import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { trainingApi, type TrainingAudience } from "../../api/endpoints/training";
import {
  HEADCOUNT_STALE_MONTHS, Modal, apiErrorMessage, btnPrimary, btnSecondary, inputCls, labelCls,
  monthsSince, td, th,
} from "./trainingUi";

function AudienceForm({ plantId, audience, onClose }: {
  plantId: string; audience?: TrainingAudience; onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState(audience?.name ?? "");
  const [headcount, setHeadcount] = useState<string>(audience ? String(audience.headcount) : "");
  const [notes, setNotes] = useState(audience?.notes ?? "");

  const mutation = useMutation({
    mutationFn: () => {
      const data = { name, headcount: Number(headcount), notes };
      return audience
        ? trainingApi.updateAudience(audience.id, data)
        : trainingApi.createAudience({ ...data, plant: plantId });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["training-audiences"] }); onClose(); },
  });

  return (
    <Modal title={audience ? t("training.audiences.edit") : t("training.audiences.new")} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className={labelCls}>{t("training.audiences.fields.name")} *</label>
          <input value={name} onChange={e => setName(e.target.value)} className={inputCls}
                 placeholder={t("training.audiences.name_placeholder")} />
        </div>
        <div>
          <label className={labelCls}>{t("training.audiences.fields.headcount")} *</label>
          <input type="number" min={0} value={headcount} onChange={e => setHeadcount(e.target.value)} className={inputCls} />
          <p className="text-xs text-gray-400 mt-1">{t("training.audiences.headcount_hint")}</p>
        </div>
        <div>
          <label className={labelCls}>{t("training.audiences.fields.notes")}</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} className={inputCls} />
        </div>
      </div>
      {mutation.isError && (
        <p className="text-sm text-red-600 mt-3">{apiErrorMessage(mutation.error, t("common.save_error"))}</p>
      )}
      <div className="flex justify-end gap-2 mt-5">
        <button onClick={onClose} className={btnSecondary}>{t("actions.cancel")}</button>
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !name.trim() || headcount === ""}
                className={btnPrimary}>
          {mutation.isPending ? t("common.saving") : t("actions.save")}
        </button>
      </div>
    </Modal>
  );
}

export function AudiencesTab({ plantId, canManage }: { plantId: string; canManage: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<TrainingAudience | null>(null);
  const [creating, setCreating] = useState(false);

  const { data: audiences = [], isLoading } = useQuery({
    queryKey: ["training-audiences", plantId],
    queryFn: () => trainingApi.audiences({ plant: plantId }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => trainingApi.deleteAudience(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["training-audiences"] }),
    onError: (e) => alert(apiErrorMessage(e, t("common.save_error"))),
  });
  const total = audiences.reduce((n, a) => n + a.headcount, 0);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="text-sm text-gray-500 max-w-3xl">{t("training.audiences.intro")}</p>
        {canManage && (
          <button onClick={() => setCreating(true)} className={btnPrimary}>{t("training.audiences.new")}</button>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : audiences.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("training.audiences.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className={th}>{t("training.audiences.fields.name")}</th>
                <th className={`${th} text-right`}>{t("training.audiences.fields.headcount")}</th>
                <th className={th}>{t("training.audiences.fields.updated_at")}</th>
                <th className={th}>{t("training.audiences.fields.notes")}</th>
                {canManage && <th className={th} />}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {audiences.map(a => {
                const stale = monthsSince(a.headcount_updated_at) >= HEADCOUNT_STALE_MONTHS;
                return (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className={`${td} font-medium text-gray-900`}>{a.name}</td>
                    <td className={`${td} text-right`}>{a.headcount}</td>
                    <td className={td}>
                      <span className="text-gray-600">{new Date(a.headcount_updated_at).toLocaleDateString(i18n.language)}</span>
                      {stale && (
                        <span className="ml-2 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
                          {t("training.audiences.stale")}
                        </span>
                      )}
                    </td>
                    <td className={`${td} text-gray-500 text-xs`}>{a.notes}</td>
                    {canManage && (
                      <td className={`${td} whitespace-nowrap text-right`}>
                        <button onClick={() => setEditing(a)} className="text-xs text-indigo-600 hover:text-indigo-800 mr-3">
                          {t("actions.edit")}
                        </button>
                        <button
                          onClick={() => window.confirm(t("training.audiences.delete_confirm", { name: a.name })) && remove.mutate(a.id)}
                          className="text-xs text-red-600 hover:text-red-800">
                          {t("actions.delete")}
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
              <tr className="bg-gray-50 font-medium">
                <td className={td}>{t("training.audiences.total")}</td>
                <td className={`${td} text-right`}>{total}</td>
                <td colSpan={canManage ? 3 : 2} />
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {creating && <AudienceForm plantId={plantId} onClose={() => setCreating(false)} />}
      {editing && <AudienceForm plantId={plantId} audience={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
