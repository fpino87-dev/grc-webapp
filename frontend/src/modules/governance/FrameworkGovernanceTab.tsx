import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { controlsApi, type FrameworkGovernanceMeta, type FrameworkImportPreview } from "../../api/endpoints/controls";

function prettyDate(d?: string | null, locale = "it") {
  if (!d) return "—";
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return String(d);
  return dt.toLocaleDateString(locale);
}

export function FrameworkGovernanceTab() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [rawJson, setRawJson] = useState<string>("");
  const [parseError, setParseError] = useState<string>("");
  const [preview, setPreview] = useState<FrameworkImportPreview | null>(null);
  const [importError, setImportError] = useState<string>("");
  const [importOk, setImportOk] = useState<string>("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["frameworks-governance"],
    queryFn: () => controlsApi.frameworksGovernance(),
    retry: false,
  });

  const importPreviewMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => controlsApi.previewFrameworkImport(payload),
    onSuccess: (p) => {
      setPreview(p);
      setParseError("");
      setImportError("");
      setImportOk("");
    },
    onError: (e: any) => {
      setPreview(null);
      setImportOk("");
      setImportError(e?.response?.data?.error || t("common.error"));
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => controlsApi.archiveFramework(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["frameworks-governance"] });
      qc.invalidateQueries({ queryKey: ["frameworks"] });
    },
    onError: (e: any) => {
      window.alert(e?.response?.data?.detail || t("common.error"));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => controlsApi.deleteFramework(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["frameworks-governance"] });
      qc.invalidateQueries({ queryKey: ["frameworks"] });
    },
    onError: (e: any) => {
      window.alert(e?.response?.data?.detail || t("common.error"));
    },
  });

  const importMutation = useMutation({
    mutationFn: ({ payload, sha256 }: { payload: Record<string, unknown>; sha256: string }) =>
      controlsApi.importFramework({ ...payload, sha256 }),
    onSuccess: (res) => {
      setImportOk(res.message || t("governance.frameworks.import_success"));
      setImportError("");
      setRawJson("");
      setPreview(null);
      qc.invalidateQueries({ queryKey: ["frameworks-governance"] });
      qc.invalidateQueries({ queryKey: ["frameworks"] });
    },
    onError: (e: any) => {
      setImportOk("");
      setImportError(e?.response?.data?.error || t("common.error"));
    },
  });

  const rows = useMemo(() => (data ?? []) as FrameworkGovernanceMeta[], [data]);

  function onLoadFile(file: File) {
    setImportOk("");
    setImportError("");
    setPreview(null);
    setParseError("");
    const reader = new FileReader();
    reader.onload = () => {
      const txt = String(reader.result || "");
      setRawJson(txt);
    };
    reader.readAsText(file);
  }

  function parsePayload(): Record<string, unknown> | null {
    setParseError("");
    if (!rawJson.trim()) {
      setParseError(t("governance.frameworks.import_missing_json"));
      return null;
    }
    try {
      const obj = JSON.parse(rawJson);
      if (!obj || typeof obj !== "object") {
        setParseError(t("governance.frameworks.import_invalid_json"));
        return null;
      }
      return obj as Record<string, unknown>;
    } catch {
      setParseError(t("governance.frameworks.import_invalid_json"));
      return null;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{t("governance.frameworks.title")}</h3>
          <p className="text-sm text-gray-500 mt-1">{t("governance.frameworks.subtitle")}</p>
        </div>
        <div className="text-xs text-gray-400 max-w-sm">
          {t("governance.frameworks.note")}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-sm text-gray-400">{t("common.loading")}</div>
        ) : error ? (
          <div className="p-6 text-sm text-red-600">{t("common.error")}</div>
        ) : rows.length === 0 ? (
          <div className="p-6 text-sm text-gray-400">{t("governance.frameworks.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("governance.frameworks.table.code")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("governance.frameworks.table.name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("governance.frameworks.table.version")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("governance.frameworks.table.published_at")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("governance.frameworks.table.controls")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("governance.frameworks.table.languages")}</th>
                <th className="px-4 py-3 w-24"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(r => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs font-bold text-gray-700">{r.code}</td>
                  <td className="px-4 py-3 text-gray-700">{r.name}</td>
                  <td className="px-4 py-3 text-gray-600">{r.version}</td>
                  <td className="px-4 py-3 text-gray-600">{prettyDate(r.published_at, i18n.language)}</td>
                  <td className="px-4 py-3 text-gray-600">
                    <span className="font-medium">{r.controls_count}</span>
                    <span className="text-xs text-gray-400 ml-2">/ {r.domains_count} {t("governance.frameworks.domains_short")}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {(r.languages ?? []).length ? (
                      <div className="flex flex-wrap gap-1">
                        {r.languages.map(l => (
                          <span key={l} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded border border-gray-200">
                            {l}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        title={t("governance.frameworks.archive_title")}
                        onClick={() => {
                          if (!window.confirm(t("governance.frameworks.archive_confirm", { code: r.code }))) return;
                          archiveMutation.mutate(r.id);
                        }}
                        disabled={archiveMutation.isPending || deleteMutation.isPending || !!r.archived_at}
                        className="text-xs text-amber-600 hover:text-amber-800 border border-amber-200 rounded px-2 py-0.5 disabled:opacity-40"
                      >
                        {t("governance.frameworks.archive_action")}
                      </button>
                      <button
                        type="button"
                        title={t("governance.frameworks.delete_title")}
                        onClick={() => {
                          if (!window.confirm(t("governance.frameworks.delete_confirm", { code: r.code }))) return;
                          deleteMutation.mutate(r.id);
                        }}
                        disabled={archiveMutation.isPending || deleteMutation.isPending}
                        className="text-xs text-red-600 hover:text-red-800 border border-red-300 rounded px-2 py-0.5 disabled:opacity-40"
                      >
                        {t("governance.frameworks.delete_action")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-800">{t("governance.frameworks.import_title")}</h4>
          <button
            type="button"
            onClick={() => {
              setRawJson("");
              setPreview(null);
              setParseError("");
              setImportError("");
              setImportOk("");
            }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {t("actions.cancel")}
          </button>
        </div>

        <input
          type="file"
          accept="application/json,.json"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onLoadFile(f);
          }}
          className="text-sm"
        />

        <textarea
          value={rawJson}
          onChange={(e) => { setRawJson(e.target.value); setPreview(null); setImportOk(""); setImportError(""); }}
          rows={8}
          placeholder={t("governance.frameworks.import_placeholder")}
          className="w-full border rounded px-3 py-2 text-xs font-mono"
        />

        {parseError && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{parseError}</div>}
        {importError && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{importError}</div>}
        {importOk && <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">{importOk}</div>}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              const payload = parsePayload();
              if (payload) importPreviewMutation.mutate(payload);
            }}
            disabled={importPreviewMutation.isPending}
            className="px-3 py-2 border rounded text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {importPreviewMutation.isPending ? t("common.loading") : t("governance.frameworks.preview_action")}
          </button>

          <button
            type="button"
            onClick={() => {
              const payload = parsePayload();
              if (payload && preview?.sha256) importMutation.mutate({ payload, sha256: preview.sha256 });
            }}
            disabled={importMutation.isPending || !preview?.sha256}
            className="px-3 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {importMutation.isPending ? t("common.saving") : t("governance.frameworks.import_confirm")}
          </button>
        </div>

        {preview && (
          <div className="mt-2 text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded p-3">
            <p className="font-semibold">{t("governance.frameworks.preview_title")}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 text-xs">
              <div>
                <div className="text-gray-500">{t("governance.frameworks.preview.framework")}</div>
                <div className="font-mono">{preview.framework.code} — {preview.framework.name}</div>
              </div>
              <div>
                <div className="text-gray-500">{t("governance.frameworks.preview.version")}</div>
                <div className="font-mono">{preview.framework.version} ({String(preview.framework.published_at)})</div>
              </div>
              <div>
                <div className="text-gray-500">{t("governance.frameworks.preview.counts")}</div>
                <div className="font-mono">
                  {preview.counts.controls} {t("governance.frameworks.controls_short")}, {preview.counts.domains} {t("governance.frameworks.domains_short")}, {preview.counts.mappings} {t("governance.frameworks.mappings_short")}
                </div>
              </div>
              <div>
                <div className="text-gray-500">{t("governance.frameworks.preview.languages")}</div>
                <div className="font-mono">{(preview.languages ?? []).join(", ") || "—"}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

