import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { DocumentOutcomeControls, PendingDocumentsPicker } from "../TargetedDocuments";
import type { ManagementReview, ReviewAgendaItem } from "../../../api/endpoints/managementReview";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: unknown) => (o && typeof o === "object" && "count" in o ? `${k}:${(o as { count: number }).count}` : k),
  }),
}));

vi.mock("../shared", () => ({ fmtDate: (d: string | null) => d ?? "—" }));

vi.mock("../../../api/endpoints/managementReview", () => ({
  managementReviewApi: {
    pendingDocuments: vi.fn(),
    addDocumentItems: vi.fn(),
    updateAgendaItem: vi.fn(),
    refreshItemVersion: vi.fn(),
    applyOutcomes: vi.fn(),
  },
  reviewErrorMessage: (_e: unknown, fallback: string) => fallback,
}));

import { managementReviewApi } from "../../../api/endpoints/managementReview";

const api = vi.mocked(managementReviewApi);

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const review = { id: "r1", kind: "mirato", agenda_items: [], approval_status: "bozza" } as unknown as ManagementReview;

function pendingRow(id: string, extra = {}) {
  return {
    id, document_code: `D-${id}`, title: `Doc ${id}`, document_type: "policy", status: "revisione",
    is_mandatory: true, plant_code: "P1", version: "Rev. 01", has_version: true, new_version: false,
    requires_body_resolution: false, selected: false, ...extra,
  };
}

function docItem(extra: Partial<ReviewAgendaItem> = {}): ReviewAgendaItem {
  return {
    id: "i1", review: "r1", code: "document", title: "[D-1] Politica", order: 0, mandatory: false,
    discussion: "", updated_at: "", document: "d1", document_outcome: "",
    document_outcome_applied_at: null, document_outcome_error: "",
    document_info: {
      id: "d1", document_code: "D-1", title: "Politica", status: "revisione", is_mandatory: true,
      examined_version: "Rev. 01", latest_version: "Rev. 01", version_changed: false,
    },
    ...extra,
  };
}

beforeEach(() => vi.clearAllMocks());

describe("PendingDocumentsPicker", () => {
  it("lists pending documents and adds only the chosen ones", async () => {
    api.pendingDocuments.mockResolvedValue([
      pendingRow("1"), pendingRow("2", { selected: true }), pendingRow("3", { has_version: false }),
    ]);
    api.addDocumentItems.mockResolvedValue({ added: ["x"], skipped: [], review });

    wrap(<PendingDocumentsPicker review={review} />);
    fireEvent.click(screen.getByText(/management_review.targeted.add_documents/));
    await waitFor(() => expect(screen.getByText("Doc 1")).toBeTruthy());

    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes[1].disabled).toBe(true);  // già all'ordine del giorno
    expect(boxes[2].disabled).toBe(true);  // senza file
    fireEvent.click(boxes[0]);
    fireEvent.click(screen.getByText("management_review.targeted.add_selected:1"));
    await waitFor(() => expect(api.addDocumentItems).toHaveBeenCalledWith("r1", ["1"]));
  });
});

describe("DocumentOutcomeControls", () => {
  it("records the outcome on the current revision", async () => {
    api.updateAgendaItem.mockResolvedValue(docItem({ document_outcome: "approvato" }));
    wrap(<DocumentOutcomeControls item={docItem()} locked={false} />);
    fireEvent.click(screen.getByText("management_review.targeted.outcomes.approvato"));
    await waitFor(() => expect(api.updateAgendaItem).toHaveBeenCalledWith("i1", { document_outcome: "approvato" }));
  });

  it("blocks the outcome and offers realign when a new revision was uploaded", async () => {
    api.refreshItemVersion.mockResolvedValue(docItem());
    const item = docItem({
      document_info: { ...docItem().document_info!, latest_version: "Rev. 02", version_changed: true },
    });
    wrap(<DocumentOutcomeControls item={item} locked={false} />);
    const approve = screen.getByText("management_review.targeted.outcomes.approvato") as HTMLButtonElement;
    expect(approve.disabled).toBe(true);
    fireEvent.click(screen.getByText("management_review.targeted.realign"));
    await waitFor(() => expect(api.refreshItemVersion).toHaveBeenCalledWith("i1"));
  });

  it("shows why an outcome was not applied", () => {
    wrap(<DocumentOutcomeControls item={docItem({ document_outcome: "approvato", document_outcome_error: "revisione cambiata" })} locked />);
    expect(screen.getByText("management_review.targeted.not_applied")).toBeTruthy();
  });
});
