import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  role: string;
  language: string;
}

interface Plant {
  id: string;
  code: string;
  name: string;
}

interface AuthStore {
  user: User | null;
  token: string | null;
  refresh: string | null;
  selectedPlant: Plant | null;
  setUser: (u: User, t: string, r?: string | null) => void;
  setToken: (t: string) => void;
  setPlant: (p: Plant) => void;
  logout: () => void;
}

// Persistenza JWT (newfix R1): senza persist, ogni F5 fa logout.
// REFRESH JWT vive 7 giorni (SIMPLE_JWT.REFRESH_TOKEN_LIFETIME) — usiamo
// localStorage per allinearci a quella durata. Il sessionStorage e' stato
// scartato perche' costringerebbe un re-login a ogni chiusura tab, che
// contraddice la durata del refresh token gia' definita lato backend.
export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refresh: null,
      selectedPlant: null,
      setUser: (user, token, refresh = null) => set({ user, token, refresh }),
      setToken: (token) => set({ token }),
      setPlant: (plant) => set({ selectedPlant: plant }),
      logout: () => set({ user: null, token: null, refresh: null, selectedPlant: null }),
    }),
    {
      name: "grc-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refresh: state.refresh,
        selectedPlant: state.selectedPlant,
      }),
    },
  ),
);
