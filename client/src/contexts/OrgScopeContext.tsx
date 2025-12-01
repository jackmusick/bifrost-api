import {
	createContext,
	useContext,
	useState,
	useEffect,
	ReactNode,
} from "react";
import { initializeBranding, applyBrandingTheme } from "@/lib/branding";

export interface OrgScope {
	type: "global" | "organization";
	orgId: string | null;
	orgName: string | null;
}

interface OrgScopeContextType {
	scope: OrgScope;
	setScope: (scope: OrgScope) => void;
	isGlobalScope: boolean;
	brandingLoaded: boolean;
	logoLoaded: boolean;
	squareLogoUrl: string | null;
	rectangleLogoUrl: string | null;
}

const OrgScopeContext = createContext<OrgScopeContextType | undefined>(
	undefined,
);

const SCOPE_STORAGE_KEY = "msp-automation-org-scope";

export function OrgScopeProvider({ children }: { children: ReactNode }) {
	const [scope, setScope] = useState<OrgScope>(() => {
		// Load from localStorage on init
		const stored = localStorage.getItem(SCOPE_STORAGE_KEY);
		if (stored) {
			try {
				return JSON.parse(stored);
			} catch {
				// Failed to parse stored scope, using default
			}
		}
		return { type: "global", orgId: null, orgName: null };
	});

	const [brandingLoaded, setBrandingLoaded] = useState(false);
	const [logoLoaded, setLogoLoaded] = useState(false);
	const [squareLogoUrl, setSquareLogoUrl] = useState<string | null>(null);
	const [rectangleLogoUrl, setRectangleLogoUrl] = useState<string | null>(
		null,
	);

	// Persist to localStorage and sessionStorage when scope changes
	useEffect(() => {
		localStorage.setItem(SCOPE_STORAGE_KEY, JSON.stringify(scope));

		// Update sessionStorage for API client (used by api.ts for X-Organization-Id header)
		if (scope.orgId) {
			sessionStorage.setItem("current_org_id", scope.orgId);
		} else {
			// Remove org ID from sessionStorage when in Global scope
			sessionStorage.removeItem("current_org_id");
		}
	}, [scope]);

	// Initialize branding when scope changes or on mount
	useEffect(() => {
		setBrandingLoaded(false);
		setLogoLoaded(false);
		setSquareLogoUrl(null);
		setRectangleLogoUrl(null);

		async function loadBrandingAndLogo() {
			try {
				// Fetch branding data (public endpoint, always GLOBAL)
				const response = await fetch("/api/branding");

				if (!response.ok) {
					// Fallback to default branding
					await initializeBranding();
					setBrandingLoaded(true);
					setLogoLoaded(true);
					return;
				}

				const branding = await response.json();
				const rectUrl = branding.rectangleLogoUrl;
				const sqUrl = branding.squareLogoUrl;

				// Preload both logos if they exist
				const preloadPromises: Promise<void>[] = [];

				if (rectUrl) {
					preloadPromises.push(
						new Promise<void>((resolve) => {
							const img = new Image();
							img.onload = () => resolve();
							img.onerror = () => resolve(); // Continue even on error
							img.src = rectUrl;
							// Timeout after 5 seconds
							setTimeout(() => resolve(), 5000);
						}),
					);
				}

				if (sqUrl) {
					preloadPromises.push(
						new Promise<void>((resolve) => {
							const img = new Image();
							img.onload = () => resolve();
							img.onerror = () => resolve();
							img.src = sqUrl;
							setTimeout(() => resolve(), 5000);
						}),
					);
				}

				// Wait for all logos to preload
				await Promise.all(preloadPromises);

				// Store logo URLs in context
				setSquareLogoUrl(sqUrl || null);
				setRectangleLogoUrl(rectUrl || null);

				// Apply branding theme (colors to CSS) - no need to fetch again
				applyBrandingTheme(branding);

				// Mark everything as loaded - UI can now render
				setBrandingLoaded(true);
				setLogoLoaded(true);
			} catch {
				// Apply default branding on error
				await initializeBranding();
				setBrandingLoaded(true);
				setLogoLoaded(true);
			}
		}

		loadBrandingAndLogo();
	}, [scope.orgId]);

	const isGlobalScope = scope.type === "global";

	return (
		<OrgScopeContext.Provider
			value={{
				scope,
				setScope,
				isGlobalScope,
				brandingLoaded,
				logoLoaded,
				squareLogoUrl,
				rectangleLogoUrl,
			}}
		>
			{children}
		</OrgScopeContext.Provider>
	);
}

export function useOrgScope() {
	const context = useContext(OrgScopeContext);
	if (!context) {
		throw new Error("useOrgScope must be used within OrgScopeProvider");
	}
	return context;
}
