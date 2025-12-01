/**
 * Organization Scope Hook
 *
 * Single source of truth for organization context.
 * Wraps the Zustand scopeStore for consistent access across the app.
 *
 * This replaces the OrgScopeContext for scope-related state.
 * For branding-related state, use useBranding hook instead.
 */

import { useScopeStore, type OrgScope } from "@/stores/scopeStore";

export type { OrgScope };

export interface UseOrgScopeReturn {
	/** Current organization scope */
	scope: OrgScope;
	/** Update the organization scope */
	setScope: (scope: OrgScope) => void;
	/** Whether currently in global (platform-wide) scope */
	isGlobalScope: boolean;
	/** Whether the store has been hydrated from localStorage */
	hasHydrated: boolean;
}

/**
 * Hook for accessing and updating organization scope.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { scope, setScope, isGlobalScope } = useOrgScope();
 *
 *   if (isGlobalScope) {
 *     return <div>Viewing global resources</div>;
 *   }
 *
 *   return <div>Viewing {scope.orgName}</div>;
 * }
 * ```
 */
export function useOrgScope(): UseOrgScopeReturn {
	const scope = useScopeStore((state) => state.scope);
	const setScope = useScopeStore((state) => state.setScope);
	const isGlobalScope = useScopeStore((state) => state.isGlobalScope);
	const hasHydrated = useScopeStore((state) => state._hasHydrated);

	return {
		scope,
		setScope,
		isGlobalScope,
		hasHydrated,
	};
}
