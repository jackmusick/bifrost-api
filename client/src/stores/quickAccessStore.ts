import { create } from "zustand";

/**
 * Quick Access state store using Zustand
 * Manages the CMD+K search modal visibility
 */

interface QuickAccessState {
	isOpen: boolean;
	openQuickAccess: () => void;
	closeQuickAccess: () => void;
	toggleQuickAccess: () => void;
}

export const useQuickAccessStore = create<QuickAccessState>((set) => ({
	isOpen: false,
	openQuickAccess: () => set({ isOpen: true }),
	closeQuickAccess: () => set({ isOpen: false }),
	toggleQuickAccess: () => set((state) => ({ isOpen: !state.isOpen })),
}));
