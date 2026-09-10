import { cn } from "@/lib/utils";
import { Outlet, useLocation } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { useAuth } from "@/contexts/AuthContext";
import { NoAccess } from "@/components/NoAccess";
import { PageLoader } from "@/components/PageLoader";
import { Skeleton } from "@/components/ui/skeleton";
import { RouteErrorBoundary } from "@/components/PageErrorBoundary";
import { useSidebar } from "@/hooks/useSidebar";
import { RouteReadyReveal } from "./RouteReadyReveal";
import { routeRevealKey as getRouteRevealKey } from "@/lib/route-reveal-key";

export function PageShell({ padded = false }: { padded?: boolean }) {
	const { isAuthenticated, isLoading, isPlatformAdmin, isOrgUser, hasRole } =
		useAuth();
	const isEmbed = hasRole("EmbedUser");
	const location = useLocation();
	const routeRevealKey = getRouteRevealKey(location.pathname, location.state);
	const {
		isMobileMenuOpen,
		setIsMobileMenuOpen,
		isSidebarCollapsed,
		toggleSidebar,
	} = useSidebar();

	// Show loading state while checking authentication
	if (isLoading) {
		return (
			<div className="min-h-screen bg-background">
				<Header />
				<div className="flex">
					<main
						className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8"
						aria-busy="true"
					>
						<p role="status" className="sr-only">
							Loading workspace
						</p>
						<div className="space-y-6" aria-hidden="true">
							<Skeleton className="h-12 w-64 max-w-full" />
							<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
								{[...Array(6)].map((_, i) => (
									<Skeleton key={i} className="h-64 w-full" />
								))}
							</div>
						</div>
					</main>
				</div>
			</div>
		);
	}

	// Authentication recovery belongs to AuthProvider, not the role-denied view.
	if (!isAuthenticated)
		return <PageLoader message="Opening sign in…" size="sm" />;

	// Show no access page if user has no role (only authenticated, no PlatformAdmin or OrgUser)
	const hasAccess = isPlatformAdmin || isOrgUser || isEmbed;
	if (!hasAccess) {
		return <NoAccess />;
	}

	// Embed users get bare content — no sidebar, header, or chrome
	if (isEmbed) {
		return (
			<RouteReadyReveal key={routeRevealKey}>
				<Outlet />
			</RouteReadyReveal>
		);
	}

	return (
		<div className="h-dvh flex bg-background overflow-hidden">
			{/* Sidebar - full height with logo */}
			<Sidebar
				isMobileMenuOpen={isMobileMenuOpen}
				setIsMobileMenuOpen={setIsMobileMenuOpen}
				isCollapsed={isSidebarCollapsed}
			/>

			{/* Main content area with header */}
			<div className="flex-1 min-w-0 flex flex-col overflow-hidden">
				<Header
					onMobileMenuToggle={() => setIsMobileMenuOpen(true)}
					onSidebarToggle={toggleSidebar}
					isSidebarCollapsed={isSidebarCollapsed}
				/>
				<main
					className={cn(
						"min-h-0 min-w-0 flex-1 overflow-auto",
						padded && "p-4 sm:p-6 lg:p-8",
					)}
				>
					<RouteErrorBoundary>
						<RouteReadyReveal key={routeRevealKey}>
							<Outlet />
						</RouteReadyReveal>
					</RouteErrorBoundary>
				</main>
			</div>
		</div>
	);
}
