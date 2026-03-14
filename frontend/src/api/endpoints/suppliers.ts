import { apiClient } from "../client";

export interface Supplier {
  id: string; name: string; vat_number: string; country: string;
  risk_level: "basso"|"medio"|"alto"|"critico"; status: "attivo"|"sospeso"|"terminato";
  contract_expiry: string | null; notes: string;
}

export const suppliersApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: Supplier[] }>("/suppliers/suppliers/", { params }).then(r => r.data),
  create: (data: Partial<Supplier>) =>
    apiClient.post<Supplier>("/suppliers/suppliers/", data).then(r => r.data),
};
