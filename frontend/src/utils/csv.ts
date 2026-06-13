// Protezione contro CSV formula injection (OWASP) per gli export CSV client-side.
// Una cella che inizia con `= + - @`, tab o CR viene interpretata come formula da
// Excel/LibreOffice/Sheets. Prefissando un apostrofo resta testo. I numeri (anche
// negativi o in notazione esponenziale) non vengono alterati.

const TRIGGER = /^[=+\-@\t\r]/;
const NUMERIC = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

/** Sanifica e quota una singola cella CSV. */
export function csvCell(value: unknown): string {
  let s = value == null ? "" : String(value);
  if (TRIGGER.test(s) && !NUMERIC.test(s)) {
    s = "'" + s;
  }
  return `"${s.replace(/"/g, '""')}"`;
}

/** Serializza righe di celle in un documento CSV (CRLF, RFC 4180). */
export function toCsv(rows: unknown[][]): string {
  return rows.map((r) => r.map(csvCell).join(",")).join("\r\n");
}
