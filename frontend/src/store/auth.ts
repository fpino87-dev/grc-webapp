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
  timezone?: string; // IANA — usato per la data "oggi" del sito (F3)
}

interface AuthStore {
  user: User | null;
  token: string | null;
  selectedPlant: Plant | null;
  setUser: (u: User, t: string) => void;
  setToken: (t: string) => void;
  setPlant: (p: Plant) => void;
  logout: () => void;
}

// newfix 2026-06-09 #6 — il refresh token NON esiste più lato JS: vive in un
// cookie httpOnly (grc_refresh) gestito dal backend, fuori dalla portata di
// qualunque XSS. L'access token (30 min) resta SOLO in memoria: dopo un F5
// viene riottenuto in silenzio da PrivateRoute via /api/token/refresh/
// (il cookie parte da solo, stessa origin). In localStorage persistono solo
// user e plant selezionato, che servono a ripartire senza flash di login.
export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      selectedPlant: null,
      setUser: (user, token) => set({ user, token }),
      setToken: (token) => set({ token }),
      setPlant: (plant) => set({ selectedPlant: plant }),
      logout: () => set({ user: null, token: null, selectedPlant: null }),
    }),
    {
      name: "grc-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        selectedPlant: state.selectedPlant,
      }),
    },
  ),
);
