import axios from "axios";

export async function loginApi(email: string, password: string) {
  const res = await axios.post("/api/token/", { username: email, password });
  return res.data as { access: string; refresh: string };
}

export async function refreshTokenApi(refresh: string) {
  const res = await axios.post("/api/token/refresh/", { refresh });
  return res.data as { access: string };
}
