import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface OrgScope {
	type: "global" | "organization";
	orgId: string | null;
	orgName: string | null;
}

interface ScopeState {
	scope: OrgScope;
	isGlobalScope: boolean;
	_hasHydrated: boolean;
	setScope: (scope: OrgScope) => void;
	setHasHydrated: (hydrated: boolean) => void;
}

// Helper to sync sessionStorage
const syncSessionStorage = (scope: OrgScope) => {
	if (scope.orgId) {
		sessionStorage.setItem("current_org_id", scope.orgId);
	} else {
		sessionStorage.removeItem("current_org_id");
	}
};

export const useScopeStore = create<ScopeState>()(
	persist(
		(set) => ({
			scope: { type: "global", orgId: null, orgName: null },
			isGlobalScope: true,
			_hasHydrated: false,
			setScope: (scope) => {
				// Update sessionStorage for API client
				syncSessionStorage(scope);

				set({
					scope,
					isGlobalScope: scope.type === "global",
				});
			},
			setHasHydrated: (hydrated) => {
				set({ _hasHydrated: hydrated });
			},
		}),
		{
			name: "msp-automation-org-scope",
			storage: createJSONStorage(() => localStorage),
			// On rehydration (initial load from localStorage), sync sessionStorage
			onRehydrateStorage: () => (state, error) => {
				// Always mark as hydrated, even if there's no stored state
				// This ensures queries aren't blocked for users without stored scope

				useScopeStore.setState({ _hasHydrated: true });

				if (!error && state) {
					// Sync sessionStorage immediately when rehydrating
					syncSessionStorage(state.scope);
				}
			},
		},
	),
);
