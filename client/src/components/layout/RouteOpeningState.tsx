import { AppLoadingSkeleton } from "@/components/jsx-app/AppLoadingSkeleton";

type OpeningKind = "agent" | "application" | "page";

function openingKind(pathname: string): OpeningKind {
	if (pathname.startsWith("/agents/")) return "agent";
	if (pathname.startsWith("/apps/")) return "application";
	return "page";
}

export function RouteOpeningState() {
	const kind = openingKind(window.location.pathname);
	const label =
		kind === "agent"
			? "Opening agent…"
			: kind === "application"
				? "Opening application…"
				: "Opening page…";

	return (
		<div className="h-dvh w-full">
			<AppLoadingSkeleton message={label} />
		</div>
	);
}

export { openingKind };
