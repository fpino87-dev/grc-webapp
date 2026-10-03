import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DecisionStep, stepStatus, type EvaluationModel, type EvaluationState } from "../EvaluationForm";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
vi.mock("../../../api/endpoints/users", () => ({ usersApi: { list: vi.fn(() => Promise.resolve([])) } }));
vi.mock("../../../api/endpoints/risk", () => ({ IMPACT_DIMENSIONS: [], riskApi: {} }));
vi.mock("../../../api/endpoints/assets", () => ({ assetsApi: {} }));
vi.mock("../../../api/endpoints/suppliers", () => ({ suppliersApi: {} }));
vi.mock("../../../api/endpoints/bia", () => ({ biaApi: {} }));
vi.mock("../../../api/endpoints/plants", () => ({ plantsApi: {} }));

const model = (current: string, extra: Partial<EvaluationModel> = {}) => ({
  threats: [], infoClasses: [], dims: {}, floor: null, floorInfo: [], dimsImpact: 3, impact: 3,
  current, expected: null, expectedBelowFloor: false, ...extra,
}) as unknown as EvaluationModel;

function renderStep(value: EvaluationState, current: string, onChange = vi.fn()) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <DecisionStep risk={{ id: "r1", plant: "p1" } as never} value={value} onChange={onChange} editable
        model={model(current)} plan={<div>PIANO</div>} acceptance={<div>ACCETTAZIONE</div>} />
    </QueryClientProvider>,
  );
  return onChange;
}

describe("DecisionStep", () => {
  it("Medium: propone di accettare il residuo; Sì registra il trattamento accettare", () => {
    const onChange = renderStep({ treatment: "" }, "medium");
    const yes = screen.getByText("risk.drawer.decision_accept").closest("button")!;
    expect(yes.textContent).toContain("risk.drawer.suggested");
    fireEvent.click(yes);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ treatment: "accettare" }));
    expect(screen.queryByText("PIANO")).toBeNull();
  });

  it("No apre il trattamento con il piano delle misure", () => {
    renderStep({ treatment: "mitigare" }, "high");
    expect(screen.getByText("PIANO")).toBeTruthy();
    expect(screen.getByText("risk.treatment_trasferire")).toBeTruthy();
  });

  it("violazione di legge o di contratto: il Sì non è disponibile", () => {
    renderStep({ treatment: "", legal_or_contract_violation: true }, "medium");
    expect(screen.getByText("risk.drawer.decision_accept").closest("button")).toBeDisabled();
    expect(screen.getByText("risk.drawer.decision_not_acceptable")).toBeTruthy();
  });

  it("stato del passo: High accettato richiede la motivazione costi/benefici", () => {
    expect(stepStatus({ treatment: "accettare", treatment_rationale: "" }, model("high")).decision).toBe(false);
    expect(stepStatus({ treatment: "accettare", treatment_rationale: "Costi superiori" }, model("high")).decision).toBe(true);
    expect(stepStatus({ treatment: "accettare" }, model("medium")).decision).toBe(true);
    expect(stepStatus({ treatment: "mitigare" }, model("high", { expected: "medium" } as never)).decision).toBe(true);
  });
});
