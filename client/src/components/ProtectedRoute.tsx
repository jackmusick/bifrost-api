import { useAuth } from "@/contexts/AuthContext";
import { NoAccess } from "@/components/NoAccess";
import { PageLoader } from "@/components/PageLoader";

interface ProtectedRouteProps {
	children: React.ReactNode;
	requirePlatformAdmin?: boolean;
	requireOrgUser?: boolean;
}

/**
 * Protected route component that checks user roles
 *
 * @param requirePlatformAdmin - Route requires PlatformAdmin role
 * @param requireOrgUser - Route requires OrgUser role (or PlatformAdmin)
 */
export function ProtectedRoute({
	children,
	requirePlatformAdmin = false,
	requireOrgUser = false,
}: ProtectedRouteProps) {
	const { isAuthenticated, isPlatformAdmin, isOrgUser, isLoading, hasRole } =
		useAuth();

	// Wait for auth to load
	if (isLoading) {
		return <PageLoader message="Loading access…" size="sm" />;
	}

	// Authentication recovery belongs to AuthProvider, not the role-denied view.
	if (!isAuthenticated)
		return <PageLoader message="Opening sign in…" size="sm" />;

	// Check for PlatformAdmin requirement
	if (requirePlatformAdmin && !isPlatformAdmin) {
		return (
			<NoAccess
				embedded
				message="You need platform administrator access to view this page. Contact your administrator if you need access."
			/>
		);
	}

	// Check for OrgUser requirement (PlatformAdmin and EmbedUser also have access)
	if (
		requireOrgUser &&
		!isOrgUser &&
		!isPlatformAdmin &&
		!hasRole("EmbedUser")
	) {
		return <NoAccess />;
	}

	return <>{children}</>;
}
