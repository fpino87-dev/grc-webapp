import { create } from "zustand";

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
  selectedPlant: Plant | null;
  setUser: (u: User, t: string) => void;
  setPlant: (p: Plant) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  selectedPlant: null,
  setUser: (user, token) => set({ user, token }),
  setPlant: (plant) => set({ selectedPlant: plant }),
  logout: () => set({ user: null, token: null, selectedPlant: null }),
}));

