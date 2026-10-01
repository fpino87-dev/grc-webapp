import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { GrcUser } from "../../api/endpoints/users";

const EXTERNAL = "__external__";

/**
 * Responsabile "misto": utente del portale OPPURE testo libero (es. fornitore
 * esterno). I due valori sono alternativi: scegliendo un utente il testo si
 * svuota, scegliendo "Altro" l'utente si azzera.
 */
export function MixedOwnerField({
  users,
  userId,
  external,
  onChange,
  noneLabel,
  small = false,
}: {
  users: GrcUser[] | undefined;
  userId: string | number | null | undefined;
  external: string | undefined;
  onChange: (userId: string | null, external: string) => void;
  noneLabel: string;
  small?: boolean;
}) {
  const { t } = useTranslation();
  const [externalMode, setExternalMode] = useState(userId == null && !!external);
  const pad = small ? "px-2 py-1.5" : "px-3 py-2";
  const selectValue = externalMode ? EXTERNAL : userId != null ? String(userId) : "";

  return (
    <div className="space-y-1.5">
      <select
        value={selectValue}
        onChange={e => {
          const v = e.target.value;
          if (v === EXTERNAL) {
            setExternalMode(true);
            onChange(null, external ?? "");
          } else {
            setExternalMode(false);
            onChange(v || null, "");
          }
        }}
        className={`w-full border rounded ${pad} text-sm`}
      >
        <option value="">{noneLabel}</option>
        {users?.map(u => (
          <option key={u.id} value={String(u.id)}>
            {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
          </option>
        ))}
        <option value={EXTERNAL}>{t("risk.owner_external_option")}</option>
      </select>
      {externalMode && (
        <input
          value={external ?? ""}
          maxLength={200}
          onChange={e => onChange(null, e.target.value)}
          placeholder={t("risk.owner_external_placeholder")}
          className={`w-full border rounded ${pad} text-sm`}
        />
      )}
    </div>
  );
}
