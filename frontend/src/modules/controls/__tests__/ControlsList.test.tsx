import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ControlsList } from "../ControlsList";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: {
    instances: vi.fn(),
    frameworks: vi.fn(),
    evaluate: vi.fn(),
    updateInstance: vi.fn(),
    deleteInstance: vi.fn(),
    propagate: vi.fn(),
    bulkApproveSoa: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/governance", () => ({
  governanceApi: { roleAssignments: vi.fn() },
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: (sel: (s: { selectedPlant: null; token: string }) => unknown) =>
    sel({ selectedPlant: null, token: "tok" }),
}));

vi.mock("../ControlDetailDrawer", () => ({
  ControlDetailDrawer: () => null,
}));

import { controlsApi } from "../../../api/endpoints/controls";

const mockInstances = vi.mocked(controlsApi.instances);
const mockFrameworks = vi.mocked(controlsApi.frameworks);
const mockEvaluate = vi.mocked(controlsApi.evaluate);
const mockUpdate = vi.mocked(controlsApi.updateInstance);

function makeInstance(overrides = {}) {
  return {
    id: "ci-1",
    control: "c-1",
    control_external_id: "A.5.1",
    control_title: "Policy di sicurezza",
    framework_code: "ISO27001",
    status: "non_valutato" as const,
    mapped_controls: [],
    calc_maturity_level: 0,
    owner: null,
    owner_display: null,
    last_evaluated_at: null,
    suggested_status: "non_valutato",
    suggestion_differs: false,
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ControlsList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockInstances.mockResolvedValue({ results: [makeInstance()], count: 1 } as never);
  mockFrameworks.mockResolvedValue([] as never);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("ControlsList — M03", () => {
  it("mostra le istanze di controllo", async () => {
    renderPage();
    expect(await screen.findByText("A.5.1")).toBeInTheDocument();
    expect(screen.getByText("Policy di sicurezza")).toBeInTheDocument();
  });

  it("il cambio stato inline passa da POST /evaluate/, mai dalla PATCH generica (C1)", async () => {
    mockEvaluate.mockResolvedValue(makeInstance({ status: "gap" }) as never);
    renderPage();
    await screen.findByText("A.5.1");

    // click sul badge stato → appare la select
    // stato e owner condividono il title "click_to_edit": lo stato è il primo
    fireEvent.click(screen.getAllByTitle("controls.actions.click_to_edit")[0]);
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "gap" } });

    await waitFor(() => expect(mockEvaluate).toHaveBeenCalledWith("ci-1", "gap", ""));
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("N/A dalla lista richiede la giustificazione e la invia a /evaluate/", async () => {
    const justification = "Controllo non applicabile a questo perimetro produttivo.";
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue(justification);
    mockEvaluate.mockResolvedValue(makeInstance({ status: "na" }) as never);
    renderPage();
    await screen.findByText("A.5.1");

    // stato e owner condividono il title "click_to_edit": lo stato è il primo
    fireEvent.click(screen.getAllByTitle("controls.actions.click_to_edit")[0]);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "na" } });

    await waitFor(() =>
      expect(mockEvaluate).toHaveBeenCalledWith("ci-1", "na", justification),
    );
    expect(mockUpdate).not.toHaveBeenCalled();
    promptSpy.mockRestore();
  });

  it("non filtra lo stato lato server: i contatori restano una distribuzione (C6)", async () => {
    renderPage();
    await screen.findByText("A.5.1");
    // la fetch dei controlli NON include il parametro status: il filtro stato è
    // client-side, quindi le pill mostrano la distribuzione reale e non vanno a 0.
    const callArg = mockInstances.mock.calls[0]?.[0] as Record<string, string> | undefined;
    expect(callArg?.status).toBeUndefined();
  });
});
