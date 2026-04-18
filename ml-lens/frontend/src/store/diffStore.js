import { create } from 'zustand'

export const useDiffStore = create((set) => ({
  diff: null,
  setDiff: (diff) => set({ diff }),
  clearDiff: () => set({ diff: null })
}))
