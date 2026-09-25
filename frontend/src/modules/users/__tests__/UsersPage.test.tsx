import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { UsersPage } from "../UsersPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn(() => Promise.resolve({ data: { results: [] } })), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: {
    list: vi.fn(() => Promise.resolve([{ id: "p1", code: "TA", name: "Plant TA" }, { id: "p2", code: "TB", name: "Plant TB" }])),
    businessUnits: vi.fn(() => Promise.resolve([])),
  },
}));
vi.mock("../../../api/endpoints/governance", () => ({
  governanceApi: {
    roleAssignments: vi.fn(() => Promise.resolve([{
      id: "r1", user: 2, role: "dpo", scope_type: "plant", scope_id: "p2", scope_code: "TB",
      valid_from: "2026-01-01", valid_until: null, is_active: true,
    }])),
    createRoleAssignment: vi.fn(), terminaRole: vi.fn(), sostituisciRole: vi.fn(),
  },
}));
vi.mock("../../../api/endpoints/users", async (orig) => {
  const actual = await orig<typeof import("../../../api/endpoints/users")>();
  return {
    ...actual,
    usersApi: {
      me: vi.fn(), listForAdmin: vi.fn(), roleMatrix: vi.fn(), create: vi.fn(), update: vi.fn(),
      toggleActive: vi.fn(), setPassword: vi.fn(), remove: vi.fn(),
    },
    plantAccessApi: { create: vi.fn(), remove: vi.fn(), listForUser: vi.fn() },
  };
});

import { usersApi, plantAccessApi } from "../../../api/endpoints/users";

const api = vi.mocked(usersApi);

const anna = {
  id: 2, username: "anna", email: "anna@x.it", first_name: "Anna", last_name: "Bianchi", is_active: true,
  is_staff: false, is_superuser: false, date_joined: "2026-01-01T00:00:00Z", last_login: null, grc_role: "control_owner",
  plant_access: [], mfa_enabled: false,
  accesses: [{ id: "a1", role: "control_owner", role_label: "Control Owner", scope_type: "single_plant", scope_bu_code: null, scope_plant_codes: ["TA"] }],
  responsibilities: [{ id: "r1", role: "dpo", scope_type: "plant", scope_id: "p2", scope_code: "TB", valid_until: null }],
  warnings: [{ responsibility: "r1", role: "dpo", scope_type: "plant", scope_id: "p2" }],
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter><UsersPage /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.me.mockResolvedValue({ id: 1, grc_role: "super_admin", is_superuser: false } as never);
  api.listForAdmin.mockResolvedValue([anna] as never);
  api.roleMatrix.mockResolvedValue({
    roles: ["super_admin", "compliance_officer", "risk_manager", "plant_manager", "control_owner", "internal_auditor", "external_auditor"],
    areas: [{ key: "pdca", perms: { super_admin: "W", compliance_officer: "W", risk_manager: "W", plant_manager: "W", control_owner: "W", internal_auditor: "R", external_auditor: "R" } }],
  } as never);
});

describe("Gestione utenti", () => {
  it("l'elenco descrive accessi, responsabilità e avvisi in chiaro", async () => {
    renderPage();
    expect(await screen.findByText(/users\.role\.control_owner\.name · TA/)).toBeInTheDocument();
    expect(screen.getByText(/governance\.roles\.dpo · TB/)).toBeInTheDocument();
    expect(screen.getAllByText(/users\.list\.gap_badge/).length).toBeGreaterThan(0);
  });

  it("il filtro stato mostra i disattivati", async () => {
    renderPage();
    await screen.findByText("Anna Bianchi");
    fireEvent.click(screen.getByRole("radio", { name: "users.filters.status_inactive" }));
    await vi.waitFor(() => expect(api.listForAdmin).toHaveBeenCalledWith("inactive"));
  });

  it("dalla responsabilità scoperta si dà l'accesso sul perimetro giusto", async () => {
    vi.mocked(plantAccessApi.create).mockResolvedValue({} as never);
    renderPage();
    fireEvent.click(await screen.findByText("Anna Bianchi"));
    const drawer = screen.getByRole("dialog");
    fireEvent.click(within(drawer).getByText("users.drawer.tabs.responsibilities"));
    fireEvent.click(await within(drawer).findByText("users.drawer.give_access"));
    // DPO non è un ruolo di accesso: si sceglie il ruolo, il sito è già TB
    expect(within(drawer).getByRole("button", { name: "TB" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(within(drawer).getByRole("button", { name: /users\.role\.internal_auditor\.name/ }));
    fireEvent.click(within(drawer).getByText("users.editor.save"));
    await vi.waitFor(() => expect(plantAccessApi.create).toHaveBeenCalledWith({
      user: 2, role: "internal_auditor", scope_type: "single_plant", scope_plants: ["p2"],
    }));
  });

  it("nuovo utente guidato: chi, ruolo, siti, riepilogo", async () => {
    api.create.mockResolvedValue({ id: 9 } as never);
    renderPage();
    fireEvent.click(await screen.findByText(/users\.wizard\.open/));
    fireEvent.change(screen.getByLabelText("users.fields.email *"), { target: { value: "marco@x.it" } });
    fireEvent.change(screen.getByLabelText("users.fields.username *"), { target: { value: "marco" } });
    fireEvent.change(screen.getByLabelText("users.fields.password *"), { target: { value: "Password-Lunga-2026" } });
    fireEvent.click(screen.getByText("users.wizard.next"));
    fireEvent.click(screen.getByRole("button", { name: /users\.role\.risk_manager\.name/ }));
    fireEvent.click(screen.getByText("users.wizard.next"));
    fireEvent.click(await screen.findByRole("button", { name: "TA" }));
    fireEvent.click(screen.getByRole("button", { name: "TB" }));
    fireEvent.click(screen.getByText("users.wizard.next"));
    fireEvent.click(screen.getByText("users.wizard.create"));
    await vi.waitFor(() => expect(api.create).toHaveBeenCalledWith(expect.objectContaining({
      username: "marco", accesses: [{ role: "risk_manager", scope_type: "plant_list", scope_plants: ["p1", "p2"] }],
    })));
  });

  it("la vista Ruoli mostra la matrice dei permessi", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("users.tabs.roles"));
    expect(await screen.findByText("users.areas.pdca")).toBeInTheDocument();
    expect(screen.getByText("users.roles_catalog.matrix_title")).toBeInTheDocument();
  });
});
