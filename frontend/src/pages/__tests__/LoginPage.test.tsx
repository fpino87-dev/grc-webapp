import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "../LoginPage";

// ── Mock dipendenze esterne ───────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../store/auth", () => ({
  useAuthStore: () => ({ setUser: vi.fn() }),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../../api/endpoints/auth", () => ({
  loginApi: vi.fn(),
  verifyMfaApi: vi.fn(),
}));

import { loginApi, verifyMfaApi } from "../../api/endpoints/auth";

const mockLoginApi = vi.mocked(loginApi);
const mockVerifyMfaApi = vi.mocked(verifyMfaApi);

// ── Helper ────────────────────────────────────────────────────────────────────

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

// ── Test ──────────────────────────────────────────────────────────────────────

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("mostra il form credenziali all'avvio", () => {
    renderLogin();
    expect(screen.getByPlaceholderText("auth.login.email_placeholder")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "auth.login.submit" })).toBeInTheDocument();
  });

  it("login senza MFA naviga alla home", async () => {
    mockLoginApi.mockResolvedValue({
      mfa_required: false,
      access: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMSIsInJvbGUiOiJ1c2VyIiwiZW1haWwiOiJ0QHQuY29tIn0.sig",
      refresh: "refresh_token",
    });

    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("auth.login.email_placeholder"), "test@test.com");
    await userEvent.type(screen.getByLabelText(/password/i), "password123");
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/"));
  });

  it("login con MFA mostra step OTP", async () => {
    mockLoginApi.mockResolvedValue({
      mfa_required: true,
      mfa_token: "test-mfa-token",
    });

    renderLogin();
    const emailInput = screen.getByPlaceholderText("auth.login.email_placeholder");
    await userEvent.type(emailInput, "mfa@test.com");
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("000000")).toBeInTheDocument();
    });
  });

  it("step OTP mostra checkbox trust device", async () => {
    mockLoginApi.mockResolvedValue({
      mfa_required: true,
      mfa_token: "test-mfa-token",
    });

    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));

    await waitFor(() => {
      expect(screen.getByText("auth.mfa.trust_device")).toBeInTheDocument();
    });
  });

  it("verifica OTP valido naviga alla home", async () => {
    mockLoginApi.mockResolvedValue({ mfa_required: true, mfa_token: "tok" });
    mockVerifyMfaApi.mockResolvedValue({ access: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMSIsInJvbGUiOiJ1c2VyIiwiZW1haWwiOiJ0QHQuY29tIn0.sig", refresh: "r" });

    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));

    await waitFor(() => screen.getByPlaceholderText("000000"));

    const otpInput = screen.getByPlaceholderText("000000");
    await userEvent.type(otpInput, "123456");
    fireEvent.click(screen.getByRole("button", { name: "auth.mfa.verify" }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/"));
  });

  it("OTP con trust device salva device_token in localStorage", async () => {
    mockLoginApi.mockResolvedValue({ mfa_required: true, mfa_token: "tok" });
    mockVerifyMfaApi.mockResolvedValue({
      access: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMSIsInJvbGUiOiJ1c2VyIiwiZW1haWwiOiJ0QHQuY29tIn0.sig",
      refresh: "r",
      device_token: "dt-abc123",
    });

    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));
    await waitFor(() => screen.getByPlaceholderText("000000"));

    // Spunta trust device
    const checkbox = screen.getByRole("checkbox");
    await userEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    // Inserisce OTP e verifica
    await userEvent.type(screen.getByPlaceholderText("000000"), "123456");
    fireEvent.click(screen.getByRole("button", { name: "auth.mfa.verify" }));

    await waitFor(() => {
      expect(localStorage.getItem("grc_device_token")).toBe("dt-abc123");
    });
  });

  it("codice OTP errato mostra errore", async () => {
    mockLoginApi.mockResolvedValue({ mfa_required: true, mfa_token: "tok" });
    mockVerifyMfaApi.mockRejectedValue(new Error("Invalid OTP"));

    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));
    await waitFor(() => screen.getByPlaceholderText("000000"));

    await userEvent.type(screen.getByPlaceholderText("000000"), "000000");
    fireEvent.click(screen.getByRole("button", { name: "auth.mfa.verify" }));

    await waitFor(() => {
      expect(screen.getByText("auth.mfa.invalid_code")).toBeInTheDocument();
    });
  });

  it("bottone back riporta allo step credenziali", async () => {
    mockLoginApi.mockResolvedValue({ mfa_required: true, mfa_token: "tok" });

    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));
    await waitFor(() => screen.getByText("auth.mfa.back"));

    fireEvent.click(screen.getByText("auth.mfa.back"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("auth.login.email_placeholder")).toBeInTheDocument();
    });
  });

  it("invio device_token salvato nel login successivo", async () => {
    localStorage.setItem("grc_device_token", "saved-dt");
    mockLoginApi.mockResolvedValue({ mfa_required: false, access: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMSIsInJvbGUiOiJ1c2VyIiwiZW1haWwiOiJ0QHQuY29tIn0.sig", refresh: "r" });

    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: "auth.login.submit" }));

    await waitFor(() => {
      expect(mockLoginApi).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        "saved-dt",
      );
    });
  });
});
