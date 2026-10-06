import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { AcceptanceOutcomeControls, PendingAcceptancesPicker } from "../RiskAcceptanceItems";
import type { ManagementReview, ReviewAgendaItem } from "../../../api/endpoints/managementReview";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: unknown) => (o && typeof o === "object" && "count" in o ? `${k}:${(o as { count: number }).count}` : k),
  }),
}));

vi.mock("../shared", () => ({ fmtDate: (d: string | null) => d ?? "—" }));
vi.mock("../../risk/RiskUi", () => ({ ClassBadge: ({ cls }: { cls: string }) => <span>{cls}</span> }));

vi.mock("../../../api/endpoints/managementReview", () => ({
  managementReviewApi: {
    pendingAcceptances: vi.fn(),
    addAcceptanceItems: vi.fn(),
    updateAgendaItem: vi.fn(),
  },
  reviewErrorMessage: (_e: unknown, fallback: string) => fallback,
}));

import { managementReviewApi } from "../../../api/endpoints/managementReview";

const api = vi.mocked(managementReviewApi);

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const review = { id: "r1", kind: "completo", agenda_items: [], approval_status: "bozza" } as unknown as ManagementReview;

function row(id: string, extra = {}) {
  return {
    id, risk_id: `k${id}`, risk_name: `Rischio ${id}`, plant_code: "P1", risk_class: "medium",
    rationale: "Costo sproporzionato", expires_on: "2027-10-01", upper_opinion: "not_required" as const,
    requested_at: "2026-10-01", selected: false, ...extra,
  };
}

function accItem(status: "pending" | "revoked" = "pending", extra: Partial<ReviewAgendaItem> = {}): ReviewAgendaItem {
  return {
    id: "i1", review: "r1", code: "risk_acceptance", title: "Accettazione del rischio — Malware (P1)", order: 7,
    mandatory: false, discussion: "", updated_at: "", document_outcome: "",
    document_outcome_applied_at: null, document_outcome_error: "", risk_acceptance: "a1",
    risk_acceptance_info: {
      id: "a1", risk_id: "k1", risk_name: "Malware", plant_code: "P1", risk_class: "high",
      rationale: "Misura in arrivo", expires_on: "2027-10-01", status, upper_opinion: "not_required",
    },
    ...extra,
  };
}

beforeEach(() => vi.clearAllMocks());

describe("PendingAcceptancesPicker", () => {
  it("shows how many acceptances wait and adds only the chosen ones", async () => {
    api.pendingAcceptances.mockResolvedValue([row("1"), row("2", { selected: true })]);
    api.addAcceptanceItems.mockResolvedValue({ added: ["x"], skipped: [], review });

    wrap(<PendingAcceptancesPicker review={review} />);
    // il contatore si vede prima di aprire il pannello: una sola ancora da scegliere
    await waitFor(() => expect(screen.getByText("1")).toBeTruthy());
    fireEvent.click(screen.getByText(/management_review.risk_acceptances.add/));

    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes[1].disabled).toBe(true);  // già all'ordine del giorno
    fireEvent.click(boxes[0]);
    fireEvent.click(screen.getByText("management_review.targeted.add_selected:1"));
    await waitFor(() => expect(api.addAcceptanceItems).toHaveBeenCalledWith("r1", ["1"]));
  });
});

describe("AcceptanceOutcomeControls", () => {
  it("records the outcome of the governing body", async () => {
    api.updateAgendaItem.mockResolvedValue(accItem());
    wrap(<AcceptanceOutcomeControls item={accItem()} locked={false} />);
    expect(screen.getByText(/Misura in arrivo/)).toBeTruthy();
    fireEvent.click(screen.getByText("management_review.targeted.outcomes.approvato"));
    await waitFor(() => expect(api.updateAgendaItem).toHaveBeenCalledWith("i1", { document_outcome: "approvato" }));
  });

  it("blocks the decision when the acceptance is no longer pending", () => {
    wrap(<AcceptanceOutcomeControls item={accItem("revoked")} locked={false} />);
    expect(screen.getByText("management_review.risk_acceptances.no_longer_pending")).toBeTruthy();
    const approve = screen.getByText("management_review.targeted.outcomes.approvato") as HTMLButtonElement;
    expect(approve.disabled).toBe(true);
  });
});
