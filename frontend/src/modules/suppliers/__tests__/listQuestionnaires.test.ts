import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn() },
}));

import { apiClient } from "../../../api/client";
import { suppliersApi } from "../../../api/endpoints/suppliers";

const mockGet = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("suppliersApi.listQuestionnaires", () => {
  it("segue tutte le pagine invece di fermarsi alla prima", async () => {
    mockGet
      .mockResolvedValueOnce({ data: { results: [{ id: "q-1" }], next: "http://api/suppliers/questionnaires/?page=2" } })
      .mockResolvedValueOnce({ data: { results: [{ id: "q-2" }], next: null } });

    const result = await suppliersApi.listQuestionnaires({ supplier: "sup-1" });

    expect(result.map(q => q.id)).toEqual(["q-1", "q-2"]);
    expect(mockGet).toHaveBeenCalledTimes(2);
    expect(mockGet.mock.calls[0][1]).toEqual({ params: { supplier: "sup-1", page_size: "500", page: "1" } });
    expect(mockGet.mock.calls[1][1]).toEqual({ params: { supplier: "sup-1", page_size: "500", page: "2" } });
  });

  it("accetta anche una risposta non paginata", async () => {
    mockGet.mockResolvedValueOnce({ data: [{ id: "q-1" }] });
    const result = await suppliersApi.listQuestionnaires();
    expect(result.map(q => q.id)).toEqual(["q-1"]);
  });
});
