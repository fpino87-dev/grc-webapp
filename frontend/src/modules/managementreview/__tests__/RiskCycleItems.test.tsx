import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { PendingRiskCyclesPicker, RiskCycleOutcomeControls } from "../RiskCycleItems";
import type { ManagementReview, ReviewAgendaItem } from "../../../api/endpoints/managementReview";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: unknown) => (o && typeof o === "object" && "count" in o ? `${k}:${(o as { count: number }).count}` : k),
  }),
}));

vi.mock("../shared", () => ({ fmtDate: (d: string | null) => d ?? "—" }));

vi.mock("../../../api/endpoints/managementReview", () => ({
  managementReviewApi: {
    pendingRiskCycles: vi.fn(),
    addRiskCycleItems: vi.fn(),
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

function review(body: string | null = "b1") {
  return { id: "r1", kind: "completo", agenda_items: [], approval_status: "bozza", governing_body: body } as unknown as ManagementReview;
}

const info = (status: "in_approvazione" | "in_corso" = "in_approvazione") => ({
  id: "c1", plant_id: "p1", plant_code: "P1", register: "P1 — Sito uno", kind: "primo" as const,
  status, started_at: "2026-09-01", risks_count: 12,
});

function cycleItem(status: "in_approvazione" | "in_corso" = "in_approvazione"): ReviewAgendaItem {
  return {
    id: "i1", review: "r1", code: "risk_cycle", title: "Approvazione della valutazione dei rischi — P1", order: 8,
    mandatory: false, discussion: "", updated_at: "", document_outcome: "",
    document_outcome_applied_at: null, document_outcome_error: "", risk_cycle: "c1", risk_cycle_info: info(status),
  };
}

beforeEach(() => vi.clearAllMocks());

describe("PendingRiskCyclesPicker", () => {
  it("adds only the chosen assessments", async () => {
    api.pendingRiskCycles.mockResolvedValue([{ ...info(), selected: false }, { ...info(), id: "c2", selected: true }]);
    api.addRiskCycleItems.mockResolvedValue({ added: ["x"], skipped: [], review: review() });

    wrap(<PendingRiskCyclesPicker review={review()} />);
    await waitFor(() => expect(screen.getByText("1")).toBeTruthy());
    fireEvent.click(screen.getByText(/management_review.risk_cycles.add/));

    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes[1].disabled).toBe(true);
    fireEvent.click(boxes[0]);
    fireEvent.click(screen.getByText("management_review.targeted.add_selected:1"));
    await waitFor(() => expect(api.addRiskCycleItems).toHaveBeenCalledWith("r1", ["c1"]));
  });
});

describe("RiskCycleOutcomeControls", () => {
  it("records the approval of the governing body", async () => {
    api.updateAgendaItem.mockResolvedValue(cycleItem());
    wrap(<RiskCycleOutcomeControls item={cycleItem()} review={review()} locked={false} />);
    fireEvent.click(screen.getByText("management_review.targeted.outcomes.approvato"));
    await waitFor(() => expect(api.updateAgendaItem).toHaveBeenCalledWith("i1", { document_outcome: "approvato" }));
  });

  it("cannot approve without the governing body of the review", () => {
    wrap(<RiskCycleOutcomeControls item={cycleItem()} review={review(null)} locked={false} />);
    expect(screen.getByText("management_review.risk_cycles.body_required")).toBeTruthy();
    const approve = screen.getByText("management_review.targeted.outcomes.approvato") as HTMLButtonElement;
    expect(approve.disabled).toBe(true);
  });

  it("blocks the decision when the assessment is no longer awaiting approval", () => {
    wrap(<RiskCycleOutcomeControls item={cycleItem("in_corso")} review={review()} locked={false} />);
    expect(screen.getByText("management_review.risk_cycles.no_longer_pending")).toBeTruthy();
  });
});
