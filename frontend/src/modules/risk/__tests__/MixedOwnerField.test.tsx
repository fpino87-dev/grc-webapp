import { describe, it, expect, vi } from "vitest";
import { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MixedOwnerField } from "../MixedOwnerField";
import type { GrcUser } from "../../../api/endpoints/users";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));

const users = [
  { id: 7, username: "mrossi", email: "m.rossi@x.it", first_name: "Mario", last_name: "Rossi" },
] as GrcUser[];

function Harness({ onChange, initial = { userId: null as string | null, external: "" } }: {
  onChange: (u: string | null, e: string) => void;
  initial?: { userId: string | null; external: string };
}) {
  const [v, setV] = useState(initial);
  return (
    <MixedOwnerField
      users={users}
      userId={v.userId}
      external={v.external}
      noneLabel="none"
      onChange={(u, e) => { setV({ userId: u, external: e }); onChange(u, e); }}
    />
  );
}

describe("MixedOwnerField", () => {
  it("sceglie un utente del portale e svuota il testo", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "7" } });
    expect(onChange).toHaveBeenLastCalledWith("7", "");
    expect(screen.queryByPlaceholderText("risk.owner_external_placeholder")).toBeNull();
  });

  it("con 'Altro' mostra il testo libero e azzera l'utente", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} initial={{ userId: "7", external: "" }} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "__external__" } });
    expect(onChange).toHaveBeenLastCalledWith(null, "");
    fireEvent.change(screen.getByPlaceholderText("risk.owner_external_placeholder"), { target: { value: "MSP Srl" } });
    expect(onChange).toHaveBeenLastCalledWith(null, "MSP Srl");
  });

  it("apre in modalità testo libero se il valore salvato è esterno", () => {
    render(<Harness onChange={vi.fn()} initial={{ userId: null, external: "Fornitore PLC" }} />);
    expect(screen.getByDisplayValue("Fornitore PLC")).toBeTruthy();
  });
});
