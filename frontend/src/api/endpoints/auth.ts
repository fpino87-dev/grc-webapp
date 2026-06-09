import axios from "axios";
import { apiClient } from "../client";
import { useAuthStore } from "../../store/auth";

// newfix #6 — il refresh token non compare mai nelle risposte: il backend lo
// imposta come cookie httpOnly (grc_refresh). Qui circola solo l'access.
export type LoginResult =
  | { mfa_required: false; access: string }
  | { mfa_required: true; mfa_token: string };

export async function loginApi(email: string, password: string, deviceToken?: string): Promise<LoginResult> {
  const body: Record<string, string> = { username: email, password };
  if (deviceToken) body.device_token = deviceToken;
  const res = await axios.post("/api/token/", body);
  if (res.status === 202) {
    return { mfa_required: true, mfa_token: res.data.mfa_token };
  }
  return { mfa_required: false, access: res.data.access };
}

export async function verifyMfaApi(mfa_token: string, otp_code: string, trust_device = false) {
  const res = await axios.post("/api/token/mfa/", { mfa_token, otp_code, trust_device });
  return res.data as { access: string; device_token?: string };
}

/**
 * Blacklista il refresh token lato server (newfix 2026-06-09 #2).
 * Best-effort: se rete/token falliscono il logout client procede comunque,
 * quindi gli errori vengono inghiottiti. Da chiamare PRIMA di svuotare lo store.
 */
export async function logoutApi(): Promise<void> {
  const { token } = useAuthStore.getState();
  if (!token) return;
  try {
    // Il refresh da blacklistare viaggia nel cookie httpOnly; la risposta
    // cancella il cookie stesso.
    await axios.post(
      "/api/token/logout/",
      {},
      { headers: { Authorization: `Bearer ${token}` } },
    );
  } catch {
    // best-effort: il logout client non deve dipendere dal server
  }
}

// Il cookie grc_refresh parte automaticamente (stessa origin).
export async function refreshTokenApi() {
  const res = await axios.post("/api/token/refresh/", {});
  return res.data as { access: string };
}

export async function getMfaStatusApi(): Promise<{ enabled: boolean }> {
  const res = await apiClient.get("/auth/mfa/status/");
  return res.data;
}

export async function getMfaSetupApi(): Promise<{
  secret: string;
  otpauth_url: string;
  qr_png: string;
}> {
  const res = await apiClient.get("/auth/mfa/setup/");
  return res.data;
}

export async function confirmMfaApi(code: string): Promise<void> {
  await apiClient.post("/auth/mfa/setup/", { code });
}

export async function disableMfaApi(code: string): Promise<void> {
  await apiClient.delete("/auth/mfa/device/", { data: { code } });
}
