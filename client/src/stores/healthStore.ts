import { create } from "zustand";

export type HealthStatus = "unknown" | "healthy" | "unhealthy" | "checking";

interface HealthState {
	status: HealthStatus;
	lastChecked: Date | null;
	errorCount: number;
	setStatus: (status: HealthStatus) => void;
	markUnhealthy: () => void;
	resetHealth: () => void;
	incrementErrorCount: () => void;
}

export const useHealthStore = create<HealthState>((set) => ({
	status: "unknown",
	lastChecked: null,
	errorCount: 0,
	setStatus: (status) =>
		set({
			status,
			lastChecked: new Date(),
		}),
	markUnhealthy: () =>
		set({
			status: "unhealthy",
			lastChecked: new Date(),
		}),
	resetHealth: () =>
		set({
			status: "unknown",
			lastChecked: null,
			errorCount: 0,
		}),
	incrementErrorCount: () =>
		set((state) => ({
			errorCount: state.errorCount + 1,
		})),
}));
