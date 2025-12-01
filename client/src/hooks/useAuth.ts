import { useEffect, useState } from "react";

export interface SWAUser {
	identityProvider: string;
	userId: string;
	userDetails: string;
	userRoles: string[];
}

export interface AuthState {
	clientPrincipal: SWAUser | null;
}

/**
 * Hook to get current authenticated user from SWA /.auth/me endpoint
 *
 * Automatically redirects to login if user is not authenticated.
 * Exposes user roles assigned by the /api/GetRoles function.
 */
export function useAuth() {
	const [authState, setAuthState] = useState<AuthState | null>(null);
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		fetch("/.auth/me")
			.then((res) => res.json())
			.then((data) => {
				setAuthState(data);
				setIsLoading(false);

				// If no user is authenticated, redirect to login
				if (!data.clientPrincipal) {
					window.location.href = "/.auth/login/aad";
				}
			})
			.catch(() => {
				setIsLoading(false);
				// On error, also redirect to login
				console.error("Error fetching auth state");
				window.location.href = "/.auth/login/aad";
			});
	}, []);

	const user = authState?.clientPrincipal;
	let roles = user?.userRoles || [];

	// Local dev: SWA CLI doesn't call rolesSource, so we simulate it
	// In production, roles come from /api/GetRoles via SWA
	const isLocalDev = import.meta.env.DEV;
	if (isLocalDev && user && roles.length <= 2) {
		// Only has 'anonymous' and 'authenticated'
		// Mock roles based on email for local testing
		if (user.userDetails === "jack@gocovi.com") {
			roles = ["authenticated", "PlatformAdmin"];
		} else if (user.userDetails === "jack@gocovi.dev") {
			roles = ["authenticated", "OrgUser"];
		} else {
			roles = ["authenticated", "OrgUser"];
		}
	}

	return {
		user,
		isAuthenticated: !!user,
		isLoading,
		roles,
		// Convenience helpers for checking roles
		hasRole: (role: string) => roles.includes(role),
		isPlatformAdmin: roles.includes("PlatformAdmin"),
		isOrgUser: roles.includes("OrgUser"),
	};
}

/**
 * Logout function that redirects to SWA logout endpoint
 */
export function logout() {
	window.location.href = "/.auth/logout";
}
