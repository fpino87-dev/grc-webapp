import axios from "axios";
import { apiClient } from "../client";

export type LoginResult =
  | { mfa_required: false; access: string; refresh: string }
  | { mfa_required: true; mfa_token: string };

export async function loginApi(email: string, password: string, deviceToken?: string): Promise<LoginResult> {
  const body: Record<string, string> = { username: email, password };
  if (deviceToken) body.device_token = deviceToken;
  const res = await axios.post("/api/token/", body);
  if (res.status === 202) {
    return { mfa_required: true, mfa_token: res.data.mfa_token };
  }
  return { mfa_required: false, access: res.data.access, refresh: res.data.refresh };
}

export async function verifyMfaApi(mfa_token: string, otp_code: string, trust_device = false) {
  const res = await axios.post("/api/token/mfa/", { mfa_token, otp_code, trust_device });
  return res.data as { access: string; refresh: string; device_token?: string };
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
