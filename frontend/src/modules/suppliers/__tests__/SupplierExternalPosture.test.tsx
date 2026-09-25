import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { SupplierExternalPosture } from "../SupplierExternalPosture";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }) }));
vi.mock("../../../i18n", () => ({ default: { language: "it", getFixedT: () => (k: string) => k, t: (k: string) => k } }));
vi.mock("../../../api/endpoints/osint", async (orig) => ({
  ...(await orig<typeof import("../../../api/endpoints/osint")>()),
  osintApi: { supplierPosture: vi.fn() },
}));
vi.mock("../../../api/endpoints/suppliers", async (orig) => ({
  ...(await orig<typeof import("../../../api/endpoints/suppliers")>()),
  suppliersApi: { get: vi.fn(), update: vi.fn() },
}));

import { osintApi } from "../../../api/endpoints/osint";
import { suppliersApi } from "../../../api/endpoints/suppliers";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(osintApi.supplierPosture).mockResolvedValue([{
    entity: "e1", domain: "x.it", name: "X", security: 40, grade: "D", last_scan_at: null,
    deep_monitoring: true, service_hosts: [], critical_open: [], reports: [],
  }] as never);
  vi.mocked(suppliersApi.get).mockResolvedValue({ id: "s1", service_urls: ["https://portale.x.it"] } as never);
  vi.mocked(suppliersApi.update).mockResolvedValue({} as never);
});

describe("Scheda fornitore — postura esterna", () => {
  it("mostra il voto e permette di indicare i servizi usati", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={qc}><MemoryRouter><SupplierExternalPosture supplierId="s1" /></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByText("https://portale.x.it")).toBeInTheDocument();
    expect(screen.getByText("osint.chain.deep_badge")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("suppliers.external.services_add"), { target: { value: "sftp.x.it" } });
    fireEvent.click(screen.getByRole("button", { name: "suppliers.external.services_add" }));
    await vi.waitFor(() => expect(suppliersApi.update).toHaveBeenCalledWith("s1", { service_urls: ["https://portale.x.it", "sftp.x.it"] }));
  });
});
