import axios from "axios";
import { apiClient } from "../client";

export type LoginResult =
  | { mfa_required: false; access: string; refresh: string }
  | { mfa_required: true; mfa_token: string };

export async function loginApi(email: string, password: string): Promise<LoginResult> {
  const res = await axios.post("/api/token/", { username: email, password });
  if (res.status === 202) {
    return { mfa_required: true, mfa_token: res.data.mfa_token };
  }
  return { mfa_required: false, access: res.data.access, refresh: res.data.refresh };
}

export async function verifyMfaApi(mfa_token: string, otp_code: string) {
  const res = await axios.post("/api/token/mfa/", { mfa_token, otp_code });
  return res.data as { access: string; refresh: string };
}

export async function refreshTokenApi(refresh: string) {
  const res = await axios.post("/api/token/refresh/", { refresh });
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
