import axios, { AxiosError, AxiosRequestConfig } from "axios";
import i18n from "../i18n";
import { useAuthStore } from "../store/auth";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const lang = i18n.language || localStorage.getItem("grc_lang") || "it";
  config.headers["Accept-Language"] = lang;
  return config;
});

// Token refresh in-flight: condiviso tra richieste parallele in 401 per evitare
// di chiamare /api/token/refresh/ N volte. La prima 401 fa refresh, le altre
// si agganciano alla stessa Promise.
let refreshInFlight: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const refreshToken = useAuthStore.getState().refresh;
  if (!refreshToken) return null;
  try {
    const res = await axios.post("/api/token/refresh/", { refresh: refreshToken });
    const newAccess: string = res.data.access;
    useAuthStore.getState().setToken(newAccess);
    return newAccess;
  } catch {
    return null;
  }
}

function logoutAndRedirect() {
  useAuthStore.getState().logout();
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = err.response?.status;

    if (status !== 401 || !original) {
      return Promise.reject(err);
    }
    // Evita loop su refresh stesso o richieste gia' ritentate.
    if (original._retry || (typeof original.url === "string" && original.url.includes("/token/refresh"))) {
      logoutAndRedirect();
      return Promise.reject(err);
    }
    if (!useAuthStore.getState().refresh) {
      logoutAndRedirect();
      return Promise.reject(err);
    }

    original._retry = true;
    if (!refreshInFlight) {
      refreshInFlight = performRefresh().finally(() => {
        refreshInFlight = null;
      });
    }
    const newAccess = await refreshInFlight;
    if (!newAccess) {
      logoutAndRedirect();
      return Promise.reject(err);
    }
    original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${newAccess}` };
    return apiClient.request(original);
  },
);
