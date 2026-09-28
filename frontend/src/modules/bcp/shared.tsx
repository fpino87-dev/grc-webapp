import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import type { BcpCoverage, BcpTestResult, BcpTestState } from "../../api/endpoints/bcp";

export const TEST_TYPES = ["tabletop", "drill", "full_interruption", "parallel"] as const;

/** Frequenze di test proposte: valore:unità come nel modello. */
export const FREQUENCIES = ["1:months", "3:months", "6:months", "1:years", "2:years"] as const;

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString(i18n.language || "it");
}

export function hours(v: number | null | undefined) {
  return v == null ? "—" : `${v}h`;
}

const COVERAGE_STYLE: Record<BcpCoverage, string> = {
  covered: "bg-green-100 text-green-700",
  test_expired: "bg-yellow-100 text-yellow-800",
  missing: "bg-red-100 text-red-700",
};

export function CoverageBadge({ coverage }: { coverage: BcpCoverage }) {
  const { t } = useTranslation();
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${COVERAGE_STYLE[coverage]}`}
      title={t(`bcp.coverage.hint.${coverage}`)}
    >
      {t(`bcp.coverage.state.${coverage}`)}
    </span>
  );
}

const TEST_STATE_STYLE: Record<BcpTestState, string> = {
  ok: "text-green-700",
  overdue: "text-orange-700",
  never: "text-orange-700",
};

export function TestStateLabel({ state }: { state: BcpTestState }) {
  const { t } = useTranslation();
  return <span className={`text-xs font-medium ${TEST_STATE_STYLE[state]}`}>{t(`bcp.test_state.${state}`)}</span>;
}

const RESULT_STYLE: Record<BcpTestResult, string> = {
  superato: "bg-green-100 text-green-700",
  parziale: "bg-yellow-100 text-yellow-800",
  fallito: "bg-red-100 text-red-700",
};

export function ResultBadge({ result }: { result: BcpTestResult }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${RESULT_STYLE[result]}`}>
      {t(`bcp.result.${result}`)}
    </span>
  );
}
