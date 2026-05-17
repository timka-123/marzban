import { fetch } from "service/http";
import { Setting, SettingValue } from "types/Setting";
import { create } from "zustand";

type SettingsStore = {
  settings: Setting[];
  isLoading: boolean;
  isPostLoading: boolean;
  fetchSettings: () => Promise<void>;
  setSetting: (key: string, value: SettingValue) => Promise<Setting>;
  deleteSetting: (key: string) => Promise<void>;
};

export const usePanelSettings = create<SettingsStore>((set, get) => ({
  settings: [],
  isLoading: false,
  isPostLoading: false,
  fetchSettings: () => {
    set({ isLoading: true });
    return fetch("/settings")
      .then((settings: Setting[]) => {
        set({ settings });
      })
      .finally(() => set({ isLoading: false }));
  },
  setSetting: (key, value) => {
    set({ isPostLoading: true });
    return fetch(`/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: { value },
    })
      .then((updated: Setting) => {
        const existing = get().settings;
        const idx = existing.findIndex((s) => s.key === updated.key);
        const next = idx >= 0
          ? existing.map((s) => (s.key === updated.key ? updated : s))
          : [...existing, updated];
        set({ settings: next });
        return updated;
      })
      .finally(() => set({ isPostLoading: false }));
  },
  deleteSetting: (key) => {
    set({ isPostLoading: true });
    return fetch(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" })
      .then(() => {
        set({ settings: get().settings.filter((s) => s.key !== key) });
      })
      .finally(() => set({ isPostLoading: false }));
  },
}));
