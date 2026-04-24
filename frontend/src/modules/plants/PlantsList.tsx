import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { plantsApi, type Plant } from "../../api/endpoints/plants";
import { controlsApi } from "../../api/endpoints/controls";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AuthenticatedImage } from "../../components/ui/AuthenticatedImage";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";

const EU_COUNTRIES_EU = [["AT","Austria"],["BE","Belgio"],
  ["BG","Bulgaria"],["CY","Cipro"],["CZ","Repubblica Ceca"],
  ["DE","Germania"],["DK","Danimarca"],["EE","Estonia"],
  ["ES","Spagna"],["FI","Finlandia"],["FR","Francia"],
  ["GR","Grecia"],["HR","Croazia"],["HU","Ungheria"],
  ["IE","Irlanda"],["IT","Italia"],["LT","Lituania"],
  ["LU","Lussemburgo"],["LV","Lettonia"],["MT","Malta"],
  ["NL","Paesi Bassi"],["PL","Polonia"],["PT","Portogallo"],
  ["RO","Romania"],["SE","Svezia"],["SI","Slovenia"],
  ["SK","Slovacchia"]];
const EU_COUNTRIES_EXTRA = [["GB","Regno Unito"],
  ["NO","Norvegia"],["CH","Svizzera"],["TR","Turchia"],
  ["US","Stati Uniti"],["JP","Giappone"],["CN","Cina"],
  ["OTHER","Altro"]];

function resolvePlantLogoSrc(plantId: string, logoUrl?: string | null) {
  if (!logoUrl) return "";
  const value = logoUrl.trim();
  if (!value) return "";
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  return `/api/v1/plants/plants/${plantId}/logo/`;
}

function EditPlantModal({ plant, onClose }: { plant: Plant; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Plant>>({
    name: plant.name,
    country: plant.country,
    nis2_scope: plant.nis2_scope,
    status: plant.status,
    has_ot: plant.has_ot,
    logo_url: plant.logo_url ?? "",
    nis2_sector: plant.nis2_sector ?? "",
    nis2_subsector: plant.nis2_subsector ?? "",
    legal_entity_name: plant.legal_entity_name ?? "",
    legal_entity_vat: plant.legal_entity_vat ?? "",
    nis2_activity_description: plant.nis2_activity_description ?? "",
    domain: plant.domain ?? "",
    additional_domains: plant.additional_domains ?? [],
  });
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const mutation = useMutation({
    mutationFn: (data: Partial<Plant>) => plantsApi.update(plant.id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["plants"] }); onClose(); },
    onError: (e: any) =>
      setError(
        e?.response?.data?.error ||
        e?.response?.data?.detail ||
        JSON.stringify(e?.response?.data) ||
        t("common.error"),
      ),
  });

  function set(field: string, value: unknown) {
    setForm(f => ({ ...f, [field]: value }));
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => plantsApi.uploadLogo(plant.id, file),
    onMutate: () => {
      setUploading(true);
      setError("");
    },
    onSuccess: (updated) => {
      setForm(f => ({ ...f, logo_url: updated.logo_url ?? "" }));
      qc.invalidateQueries({ queryKey: ["plants"] });
    },
    onError: (e: any) =>
      setError(
        e?.response?.data?.error ||
        e?.response?.data?.detail ||
        JSON.stringify(e?.response?.data) ||
        t("common.error"),
      ),
    onSettled: () => setUploading(false),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-6">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl xl:max-w-5xl flex flex-col max-h-[min(92vh,920px)] my-auto">
        <div className="px-5 sm:px-6 pt-5 pb-3 shrink-0 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900">{t("plants.edit.title")}</h3>
          <p className="text-xs text-gray-400 mt-0.5 font-mono">{plant.code}</p>
        </div>

        <div className="px-5 sm:px-6 py-4 flex-1 overflow-y-auto min-h-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
            <div className="space-y-3 min-w-0">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
                <input value={form.name ?? ""} onChange={e => set("name", e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.country")}</label>
                  <select value={form.country ?? "IT"} onChange={e => set("country", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    <optgroup label="Unione Europea">
                      {EU_COUNTRIES_EU.map(([code, name]) => (
                        <option key={code} value={code}>{code} — {name}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Extra UE (non soggetti NIS2)">
                      {EU_COUNTRIES_EXTRA.map(([code, name]) => (
                        <option key={code} value={code}>{code} — {name}</option>
                      ))}
                    </optgroup>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.status")}</label>
                  <select value={form.status ?? ""} onChange={e => set("status", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    <option value="attivo">{t("status.attivo")}</option>
                    <option value="in_dismissione">{t("status.in_dismissione")}</option>
                    <option value="chiuso">{t("status.chiuso")}</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_scope")}</label>
                <select value={form.nis2_scope ?? ""} onChange={e => set("nis2_scope", e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm">
                  <option value="non_soggetto">{t("status.non_soggetto")}</option>
                  <option value="importante">{t("status.importante")}</option>
                  <option value="essenziale">{t("status.essenziale")}</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="edit_has_ot" checked={!!form.has_ot}
                  onChange={e => set("has_ot", e.target.checked)} className="rounded" />
                <label htmlFor="edit_has_ot" className="text-sm text-gray-700">{t("plants.fields.has_ot")}</label>
              </div>
            </div>

            <div className="space-y-3 min-w-0 border-t border-gray-100 pt-4 lg:border-t-0 lg:pt-0">
              <div className="text-xs font-semibold text-gray-800">{t("plants.nis2_entity.section_title")}</div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_sector")}</label>
                  <input
                    value={form.nis2_sector ?? ""}
                    onChange={e => set("nis2_sector", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={t("plants.placeholders.nis2_sector")}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_subsector")}</label>
                  <input
                    value={form.nis2_subsector ?? ""}
                    onChange={e => set("nis2_subsector", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={t("plants.placeholders.nis2_subsector")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.legal_entity_name")}</label>
                  <input
                    value={form.legal_entity_name ?? ""}
                    onChange={e => set("legal_entity_name", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.legal_entity_vat")}</label>
                  <input
                    value={form.legal_entity_vat ?? ""}
                    onChange={e => set("legal_entity_vat", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_activity_description")}</label>
                <textarea
                  value={form.nis2_activity_description ?? ""}
                  onChange={e => set("nis2_activity_description", e.target.value)}
                  rows={3}
                  className="w-full border rounded px-3 py-2 text-sm max-h-40 resize-y min-h-[4.5rem]"
                />
              </div>
              <p className="text-xs text-gray-500">{t("plants.nis2_entity.contact_hint")}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.domain")}</label>
                  <input
                    value={form.domain ?? ""}
                    onChange={e => set("domain", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder="azienda.it"
                  />
                  <p className="mt-1 text-xs text-gray-500">{t("plants.hints.domain")}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.additional_domains")}</label>
                  <textarea
                    value={(form.additional_domains ?? []).join("\n")}
                    onChange={e => set("additional_domains", e.target.value.split("\n").map(s => s.trim()).filter(Boolean))}
                    rows={3}
                    className="w-full border rounded px-3 py-2 text-sm resize-y"
                    placeholder={t("plants.placeholders.additional_domains")}
                  />
                  <p className="mt-1 text-xs text-gray-500">{t("plants.hints.additional_domains")}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.logo_url_label")}</label>
                <input
                  value={form.logo_url ?? ""}
                  onChange={e => set("logo_url", e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="https://.../logo.png"
                />
                <p className="mt-1 text-xs text-gray-500">
                  {t("plants.logo_url_hint")}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <label className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-xs font-medium text-gray-700 bg-white cursor-pointer hover:bg-gray-50">
                    <span>{uploading ? t("common.uploading") : t("plants.fields.logo_upload_label") ?? "Carica file"}</span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={e => {
                        const file = e.target.files?.[0];
                        if (file) {
                          uploadMutation.mutate(file);
                        }
                      }}
                    />
                  </label>
                  {form.logo_url && (
                    <AuthenticatedImage
                      src={resolvePlantLogoSrc(plant.id, form.logo_url)}
                      alt="Logo preview"
                      className="h-8 w-auto max-w-[120px] rounded border border-gray-200 bg-white object-contain"
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="px-5 sm:px-6 shrink-0">
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
          </div>
        )}
        <div className="px-5 sm:px-6 py-4 border-t border-gray-100 shrink-0 flex justify-end gap-2 bg-gray-50/90 rounded-b-lg">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

const EMPTY: Partial<Plant> = {
  code: "",
  name: "",
  country: "IT",
  nis2_scope: "non_soggetto",
  status: "attivo",
  has_ot: false,
  logo_url: "",
  nis2_sector: "",
  nis2_subsector: "",
  legal_entity_name: "",
  legal_entity_vat: "",
  nis2_activity_description: "",
  domain: "",
  additional_domains: [],
};

function PlantModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Plant>>(EMPTY);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: plantsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["plants"] }); onClose(); },
    onError: (e: any) =>
      setError(
        e?.response?.data?.detail ||
        JSON.stringify(e?.response?.data) ||
        t("common.save_error"),
      ),
  });

  function set(field: string, value: unknown) {
    setForm(f => ({ ...f, [field]: value }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-6">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl xl:max-w-5xl flex flex-col max-h-[min(92vh,920px)] my-auto">
        <div className="px-5 sm:px-6 pt-5 pb-3 shrink-0 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900">{t("plants.new.title")}</h3>
        </div>

        <div className="px-5 sm:px-6 py-4 flex-1 overflow-y-auto min-h-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
            <div className="space-y-3 min-w-0">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.code")} *</label>
                  <input value={form.code} onChange={e => set("code", e.target.value.toUpperCase())}
                    className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder={t("plants.placeholders.code")} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.country")}</label>
                  <select
                    value={form.country ?? "IT"}
                    onChange={e => set("country", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  >
                    <optgroup label="Unione Europea">
                      {EU_COUNTRIES_EU.map(([code, name]) => (
                        <option key={code} value={code}>{code} — {name}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Extra UE (non soggetti NIS2)">
                      {EU_COUNTRIES_EXTRA.map(([code, name]) => (
                        <option key={code} value={code}>{code} — {name}</option>
                      ))}
                    </optgroup>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
                <input value={form.name} onChange={e => set("name", e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm" placeholder={t("plants.placeholders.name")} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.status")}</label>
                  <select value={form.status} onChange={e => set("status", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    <option value="attivo">{t("status.attivo")}</option>
                    <option value="in_dismissione">{t("status.in_dismissione")}</option>
                    <option value="chiuso">{t("status.chiuso")}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_scope")}</label>
                  <select value={form.nis2_scope} onChange={e => set("nis2_scope", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    <option value="non_soggetto">{t("status.non_soggetto")}</option>
                    <option value="importante">{t("status.importante")}</option>
                    <option value="essenziale">{t("status.essenziale")}</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="has_ot" checked={!!form.has_ot}
                  onChange={e => set("has_ot", e.target.checked)} className="rounded" />
                <label htmlFor="has_ot" className="text-sm text-gray-700">{t("plants.fields.has_ot")}</label>
              </div>
            </div>

            <div className="space-y-3 min-w-0 border-t border-gray-100 pt-4 lg:border-t-0 lg:pt-0">
              <div className="text-xs font-semibold text-gray-800">{t("plants.nis2_entity.section_title")}</div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_sector")}</label>
                  <input
                    value={form.nis2_sector ?? ""}
                    onChange={e => set("nis2_sector", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={t("plants.placeholders.nis2_sector")}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_subsector")}</label>
                  <input
                    value={form.nis2_subsector ?? ""}
                    onChange={e => set("nis2_subsector", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={t("plants.placeholders.nis2_subsector")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.legal_entity_name")}</label>
                  <input
                    value={form.legal_entity_name ?? ""}
                    onChange={e => set("legal_entity_name", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.legal_entity_vat")}</label>
                  <input
                    value={form.legal_entity_vat ?? ""}
                    onChange={e => set("legal_entity_vat", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.nis2_activity_description")}</label>
                <textarea
                  value={form.nis2_activity_description ?? ""}
                  onChange={e => set("nis2_activity_description", e.target.value)}
                  rows={3}
                  className="w-full border rounded px-3 py-2 text-sm max-h-40 resize-y min-h-[4.5rem]"
                />
              </div>
              <p className="text-xs text-gray-500">{t("plants.nis2_entity.contact_hint")}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.domain")}</label>
                  <input
                    value={form.domain ?? ""}
                    onChange={e => set("domain", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder="azienda.it"
                  />
                  <p className="mt-1 text-xs text-gray-500">{t("plants.hints.domain")}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.additional_domains")}</label>
                  <textarea
                    value={(form.additional_domains ?? []).join("\n")}
                    onChange={e => set("additional_domains", e.target.value.split("\n").map(s => s.trim()).filter(Boolean))}
                    rows={3}
                    className="w-full border rounded px-3 py-2 text-sm resize-y"
                    placeholder={t("plants.placeholders.additional_domains")}
                  />
                  <p className="mt-1 text-xs text-gray-500">{t("plants.hints.additional_domains")}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.logo_url_label")}</label>
                <input
                  value={form.logo_url ?? ""}
                  onChange={e => set("logo_url", e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="https://.../logo.png"
                />
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="px-5 sm:px-6 shrink-0">
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
          </div>
        )}
        <div className="px-5 sm:px-6 py-4 border-t border-gray-100 shrink-0 flex justify-end gap-2 bg-gray-50/90 rounded-b-lg">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button onClick={() => mutation.mutate(form)} disabled={mutation.isPending || !form.code || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? t("common.saving") : t("plants.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// Raggruppa TISAX_L2 e TISAX_L3 come voce unica "TISAX"
type FwGroup = { key: string; label: string; isTisax: boolean; ids: Record<string, string> };

function buildGroups(frameworks: { id: string; code: string; name: string }[], assignedCodes: Set<string>, tisaxLabel: string): FwGroup[] {
  const groups: FwGroup[] = [];
  const tisaxL2 = frameworks.find(f => f.code === "TISAX_L2");
  const tisaxL3 = frameworks.find(f => f.code === "TISAX_L3");
  const tisaxBothAssigned = assignedCodes.has("TISAX_L2") && assignedCodes.has("TISAX_L3");
  if ((tisaxL2 || tisaxL3) && !tisaxBothAssigned) {
    groups.push({ key: "TISAX", label: tisaxLabel, isTisax: true, ids: { L2: tisaxL2?.id ?? "", L3: tisaxL3?.id ?? "" } });
  }
  for (const f of frameworks) {
    // Tutti i framework TISAX sono gestiti tramite il selettore di livello (L2 / L3 / L3+PROTO).
    if (f.code === "TISAX_L2" || f.code === "TISAX_L3" || f.code === "TISAX_PROTO") continue;
    if (assignedCodes.has(f.code)) continue;
    groups.push({ key: f.id, label: `${f.code} — ${f.name}`, isTisax: false, ids: { single: f.id } });
  }
  return groups;
}

function FrameworkPanel({ plant, onClose }: { plant: Plant; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  // "TISAX" is the virtual key for grouped TISAX entry; otherwise it's the framework id
  const [selectedKey, setSelectedKey] = useState("");
  const [tisaxLevel, setTisaxLevel] = useState<"L2" | "L3" | "L3+PROTO">("L2");
  const [nisLevel, setNisLevel] = useState<string>(plant.nis2_scope !== "non_soggetto" ? plant.nis2_scope : "importante");
  const [genericLevel, setGenericLevel] = useState("base");
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);
  const [error, setError] = useState("");

  const { data: assigned = [] } = useQuery({
    queryKey: ["plant-frameworks", plant.id],
    queryFn: () => plantsApi.plantFrameworks(plant.id),
  });

  const { data: frameworks = [] } = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => controlsApi.frameworks(),
  });

  const assignMutation = useMutation({
    mutationFn: async () => {
      if (selectedKey === "TISAX") {
        const tisaxL2Id = frameworks.find(f => f.code === "TISAX_L2")?.id;
        const tisaxL3Id = frameworks.find(f => f.code === "TISAX_L3")?.id;
        const tisaxProtoId = frameworks.find(f => f.code === "TISAX_PROTO")?.id;
        const assignedCodes = new Set(assigned.map(a => a.framework_code));
        if (tisaxLevel === "L2") {
          if (!assignedCodes.has("TISAX_L2") && tisaxL2Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL2Id, level: "AL2" });
        } else if (tisaxLevel === "L3") {
          // L3 = L2 + L3
          if (!assignedCodes.has("TISAX_L2") && tisaxL2Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL2Id, level: "AL2" });
          if (!assignedCodes.has("TISAX_L3") && tisaxL3Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL3Id, level: "AL3" });
        } else {
          // L3+PROTO = L2 + L3 + PROTO
          if (!assignedCodes.has("TISAX_L2") && tisaxL2Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL2Id, level: "AL2" });
          if (!assignedCodes.has("TISAX_L3") && tisaxL3Id)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxL3Id, level: "AL3" });
          if (!assignedCodes.has("TISAX_PROTO") && tisaxProtoId)
            await plantsApi.assignFramework({ plant: plant.id, framework: tisaxProtoId, level: "PROTO" });
        }
      } else {
        const fwCode = frameworks.find(f => f.id === selectedKey)?.code ?? "";
        const isNis = fwCode === "NIS2" || fwCode === "ACN_NIS2";
        const level = isNis ? nisLevel : genericLevel;
        await plantsApi.assignFramework({ plant: plant.id, framework: selectedKey, level });
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plant-frameworks", plant.id] });
      qc.invalidateQueries({ queryKey: ["controls"] });
      setSelectedKey("");
      setError("");
    },
    onError: (e: any) =>
      setError(
        e?.response?.data?.detail ||
        JSON.stringify(e?.response?.data) ||
        t("common.error"),
      ),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => plantsApi.toggleFramework(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plant-frameworks", plant.id] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => plantsApi.removeFramework(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plant-frameworks", plant.id] });
      qc.invalidateQueries({ queryKey: ["controls"] });
      setConfirmRemove(null);
    },
  });

  const assignedCodes = new Set(assigned.map(a => a.framework_code));
  const groups = buildGroups(frameworks, assignedCodes, t("plants.tisax_framework_label"));
  const selectedFwCode = selectedKey !== "TISAX" ? (frameworks.find(f => f.id === selectedKey)?.code ?? "") : "";
  const selectedIsNis = selectedFwCode === "NIS2" || selectedFwCode === "ACN_NIS2";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{t("plants.frameworks.title")}</h3>
            <p className="text-xs text-gray-400 mt-0.5">{plant.code} — {plant.name}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        {/* Assigned list */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
          {assigned.length === 0 ? (
            <p className="text-sm text-gray-400 italic">{t("plants.frameworks.empty")}</p>
          ) : assigned.map(pf => (
            <div key={pf.id} className="rounded-lg border border-gray-200 px-4 py-3">
              {confirmRemove === pf.id ? (
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-red-700">
                    {t("plants.frameworks.remove_confirm", { code: pf.framework_code })}
                  </p>
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => setConfirmRemove(null)} className="text-xs border rounded px-2 py-1 text-gray-600 hover:bg-gray-50">
                      {t("actions.cancel")}
                    </button>
                    <button onClick={() => removeMutation.mutate(pf.id)} disabled={removeMutation.isPending}
                      className="text-xs bg-red-600 text-white rounded px-2 py-1 hover:bg-red-700 disabled:opacity-50">
                      {removeMutation.isPending ? "..." : t("actions.delete")}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-bold text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded">{pf.framework_code}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${pf.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {pf.active ? t("common.enabled") : t("common.disabled")}
                      </span>
                      <span className="text-xs text-gray-400">{t("plants.frameworks.level", { level: pf.level })}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 leading-snug">{pf.framework_name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{t("plants.frameworks.active_from", { date: pf.active_from })}</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => toggleMutation.mutate(pf.id)} disabled={toggleMutation.isPending}
                      className="text-xs text-primary-600 hover:underline">
                      {pf.active ? t("plants.frameworks.deactivate") : t("plants.frameworks.activate")}
                    </button>
                    <button onClick={() => setConfirmRemove(pf.id)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline">
                      {t("actions.delete")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Assign footer */}
        {groups.length > 0 && (
          <div className="border-t border-gray-100 px-6 py-4 shrink-0 space-y-3">
            <p className="text-sm font-medium text-gray-700">{t("plants.frameworks.assign_new")}</p>

            {/* Framework selector */}
            <select
              value={selectedKey}
              onChange={e => { setSelectedKey(e.target.value); setError(""); }}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">{t("plants.frameworks.select")}</option>
              {groups.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
            </select>

            {/* TISAX sub-level */}
            {selectedKey === "TISAX" && (
              <div className="space-y-2">
                <div className="flex gap-3">
                  {([
                    { value: "L2",      label: t("plants.frameworks.tisax.assessment_level", { level: "L2" }),    hint: t("plants.frameworks.tisax.l2_hint") },
                    { value: "L3",      label: t("plants.frameworks.tisax.assessment_level", { level: "L3" }),    hint: t("plants.frameworks.tisax.l3_hint") },
                    { value: "L3+PROTO", label: t("plants.frameworks.tisax.l3_proto_label"),                      hint: t("plants.frameworks.tisax.l3_proto_hint") },
                  ] as const).map(opt => (
                    <label key={opt.value} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${tisaxLevel === opt.value ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}>
                      <input type="radio" name="tisax_level" value={opt.value} checked={tisaxLevel === opt.value} onChange={() => setTisaxLevel(opt.value)} className="mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{opt.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{opt.hint}</p>
                      </div>
                    </label>
                  ))}
                </div>
                {tisaxLevel === "L3" && (
                  <p className="text-xs text-blue-600 bg-blue-50 rounded px-2 py-1.5">
                    {t("plants.frameworks.tisax.l3_notice", {
                      l2: frameworks.find(f => f.code === "TISAX_L2") ? "45" : "0",
                      l3: frameworks.find(f => f.code === "TISAX_L3") ? "12" : "0",
                      total: "57",
                    })}
                  </p>
                )}
                {tisaxLevel === "L3+PROTO" && (
                  <p className="text-xs text-violet-600 bg-violet-50 rounded px-2 py-1.5">
                    {t("plants.frameworks.tisax.l3_proto_notice", {
                      l2:    frameworks.find(f => f.code === "TISAX_L2")    ? "45" : "0",
                      l3:    frameworks.find(f => f.code === "TISAX_L3")    ? "12" : "0",
                      proto: frameworks.find(f => f.code === "TISAX_PROTO") ? "22" : "0",
                      total: "79",
                    })}
                  </p>
                )}
              </div>
            )}

            {/* NIS2 level */}
            {selectedIsNis && (
              <div className="space-y-1.5">
                <div className="flex gap-3">
                  {[
                    { v: "essenziale", label: t("status.essenziale"), hint: t("plants.frameworks.nis2.essential_hint") },
                    { v: "importante", label: t("status.importante"),  hint: t("plants.frameworks.nis2.important_hint") },
                  ].map(o => (
                    <label key={o.v} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${nisLevel === o.v ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}>
                      <input type="radio" name="nis_level" value={o.v} checked={nisLevel === o.v} onChange={() => setNisLevel(o.v)} className="mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{o.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{o.hint}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Generic level (ISO etc.) */}
            {selectedKey && selectedKey !== "TISAX" && !selectedIsNis && (
              <select value={genericLevel} onChange={e => setGenericLevel(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500">
                <option value="base">{t("plants.frameworks.generic.base")}</option>
                <option value="avanzato">{t("plants.frameworks.generic.advanced")}</option>
                <option value="completo">{t("plants.frameworks.generic.complete")}</option>
              </select>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}

            {selectedKey && (
              <button
                onClick={() => assignMutation.mutate()}
                disabled={assignMutation.isPending}
                className="w-full py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
              >
                {assignMutation.isPending ? t("plants.frameworks.assigning") : t("plants.frameworks.assign")}
              </button>
            )}
            <p className="text-xs text-gray-400">{t("plants.frameworks.assign_help")}</p>
          </div>
        )}

        {groups.length === 0 && assigned.length > 0 && (
          <div className="border-t border-gray-100 px-6 py-3 shrink-0">
            <p className="text-xs text-gray-400">{t("plants.frameworks.all_assigned")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export function PlantsList() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [editPlant, setEditPlant] = useState<Plant | null>(null);
  const [frameworkPlant, setFrameworkPlant] = useState<Plant | null>(null);
  const { data: plants, isLoading } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const { setPlant } = useAuthStore();

  const [deleteBlocked, setDeleteBlocked] = useState<{ id: string; blocking: Record<string, number> } | null>(null);

  const deleteMutation = useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) => plantsApi.remove(id, force),
    onSuccess: () => {
      setDeleteBlocked(null);
      qc.invalidateQueries({ queryKey: ["plants"] });
    },
    onError: (e: any, vars) => {
      const blocking = e?.response?.data?.blocking;
      if (blocking && Object.keys(blocking).length > 0) {
        setDeleteBlocked({ id: vars.id, blocking });
      } else {
        window.alert(e?.response?.data?.detail || t("common.error"));
      }
    },
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("plants.title")}</h2>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          {t("plants.new.open")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : !plants?.length ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">{t("plants.empty")}</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">
              {t("plants.new.first")}
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600"></th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.code")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.country")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.nis2")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.table.ot")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {plants.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    {p.logo_url ? (
                      <AuthenticatedImage
                        src={resolvePlantLogoSrc(p.id, p.logo_url)}
                        alt={p.name}
                        className="h-6 w-auto object-contain rounded-sm border border-gray-200 bg-white"
                      />
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs font-bold text-gray-700">{p.code}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{p.name}</td>
                  <td className="px-4 py-3 text-gray-500 uppercase text-xs">{p.country}</td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3">
                    {p.nis2_scope !== "non_soggetto"
                      ? <StatusBadge status={p.nis2_scope} />
                      : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {p.has_ot
                      ? <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">OT</span>
                      : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => setEditPlant(p)}
                        className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded px-1.5 py-0.5 hover:bg-gray-50"
                        title={t("plants.actions.edit_title")}>✏</button>
                      <button
                        onClick={() => {
                          const ok = window.confirm(t("plants.actions.delete_confirm", { name: p.name }));
                          if (!ok) return;
                          deleteMutation.mutate({ id: p.id });
                        }}
                        disabled={deleteMutation.isPending}
                        className="text-xs text-red-600 hover:text-red-700 border border-red-200 rounded px-1.5 py-0.5 hover:bg-red-50 disabled:opacity-50"
                        title={t("plants.actions.delete_title")}
                      >
                        🗑
                      </button>
                      <button onClick={() => setFrameworkPlant(p)}
                        className="text-xs text-indigo-600 hover:underline">
                        {t("plants.actions.frameworks")}
                      </button>
                      <button onClick={() => setPlant({ id: p.id, code: p.code, name: p.name })}
                        className="text-xs text-primary-600 hover:underline">
                        {t("plants.actions.select")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <PlantModal onClose={() => setShowNew(false)} />}
      {editPlant && <EditPlantModal plant={editPlant} onClose={() => setEditPlant(null)} />}
      {frameworkPlant && <FrameworkPanel plant={frameworkPlant} onClose={() => setFrameworkPlant(null)} />}

      {deleteBlocked && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {t("plants.delete_blocked.title")}
            </h3>
            <p className="text-sm text-gray-600 mb-4">{t("plants.delete_blocked.intro")}</p>
            <ul className="space-y-1 mb-4">
              {Object.entries(deleteBlocked.blocking).map(([key, count]) => (
                <li key={key} className="flex items-center justify-between text-sm px-3 py-1.5 bg-red-50 border border-red-100 rounded">
                  <span className="text-gray-700">
                    {t(`plants.delete_blocked.deps.${key}`, { defaultValue: key })}
                  </span>
                  <span className="font-semibold text-red-700">{count}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-gray-500 mb-5">{t("plants.delete_blocked.force_hint")}</p>
            <div className="flex justify-between gap-3">
              <button
                onClick={() => setDeleteBlocked(null)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                {t("actions.cancel")}
              </button>
              <button
                onClick={() => {
                  if (!window.confirm(t("plants.delete_blocked.force_confirm"))) return;
                  deleteMutation.mutate({ id: deleteBlocked.id, force: true });
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-md font-medium disabled:opacity-50"
              >
                {deleteMutation.isPending ? "..." : t("plants.delete_blocked.force_action")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
