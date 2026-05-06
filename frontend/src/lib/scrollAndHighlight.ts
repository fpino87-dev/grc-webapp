/**
 * Scrolla nella vista la riga con `data-row-id="${rowId}"` e la evidenzia per
 * ~2.5s. Usato dal GRC Assistant per atterrare sull'item specifico (documento,
 * rischio, fornitore) cliccando "Vai a risolvere".
 *
 * Polling fino a 2s perche' i dati arrivano via TanStack Query e la riga
 * potrebbe non essere ancora nel DOM al primo render.
 */
export function scrollAndHighlight(rowId: string): void {
  if (!rowId) return;

  let attempts = 0;
  const maxAttempts = 25; // 25 * 100ms = 2.5s

  function tryFind(): void {
    attempts++;
    const el = document.querySelector(
      `[data-row-id="${CSS.escape(rowId)}"]`,
    ) as HTMLElement | null;

    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("grc-row-highlight");
      window.setTimeout(() => {
        el.classList.remove("grc-row-highlight");
      }, 2500);
      return;
    }

    if (attempts < maxAttempts) {
      window.setTimeout(tryFind, 100);
    }
  }

  tryFind();
}
