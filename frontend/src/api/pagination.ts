import { apiClient } from "./client";

/**
 * Legge TUTTE le pagine di un elenco DRF.
 *
 * Il backend pagina a 25 elementi (PAGE_SIZE): chi prende solo `results`
 * della prima risposta vede al massimo i primi 25 record, e ricerche/filtri
 * lato client lavorano su quel sottoinsieme. Qui si seguono le pagine (500 per
 * richiesta, max consentito dal server 1000) finché `next` è null. Gli
 * endpoint non paginati (che rispondono con un array) sono restituiti così.
 */
export async function fetchAllPages<T>(url: string, params?: Record<string, string>): Promise<T[]> {
  const all: T[] = [];
  for (let page = 1; ; page++) {
    const { data } = await apiClient.get<{ results: T[]; next: string | null } | T[]>(url, {
      params: { page_size: "500", ...params, page: String(page) },
    });
    if (Array.isArray(data)) return data;
    all.push(...data.results);
    if (!data.next) return all;
  }
}
