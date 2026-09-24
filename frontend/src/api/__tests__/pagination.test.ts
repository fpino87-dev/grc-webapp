import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../client", () => ({ apiClient: { get: vi.fn() } }));

import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

const get = vi.mocked(apiClient.get);

beforeEach(() => get.mockReset());

describe("fetchAllPages", () => {
  it("segue le pagine finché next è null", async () => {
    get
      .mockResolvedValueOnce({ data: { results: [1, 2], next: "p2" } } as never)
      .mockResolvedValueOnce({ data: { results: [3], next: null } } as never);
    expect(await fetchAllPages<number>("/x/", { status: "attivo" })).toEqual([1, 2, 3]);
    expect(get).toHaveBeenNthCalledWith(1, "/x/", { params: { page_size: "500", status: "attivo", page: "1" } });
    expect(get).toHaveBeenNthCalledWith(2, "/x/", { params: { page_size: "500", status: "attivo", page: "2" } });
  });

  it("restituisce l'array degli endpoint non paginati", async () => {
    get.mockResolvedValueOnce({ data: [7, 8] } as never);
    expect(await fetchAllPages<number>("/y/")).toEqual([7, 8]);
    expect(get).toHaveBeenCalledTimes(1);
  });
});
