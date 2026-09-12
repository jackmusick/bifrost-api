import { ArrowLeft, RefreshCw } from "lucide-react";
import { Link, useRouteError } from "react-router-dom";

import { RouteUnavailableState } from "./RouteUnavailableState";
import { Button } from "@/components/ui/button";

export function RouteLoadError() {
	const error = useRouteError();
	const isAgent = window.location.pathname.startsWith("/agents/");
	const entity = isAgent ? "agent" : "application";
	const returnPath = isAgent ? "/agents" : "/apps";
	const detail =
		error instanceof Error
			? error.message
			: `The ${entity} could not be loaded.`;

	return (
		<RouteUnavailableState
			title={`Couldn't open this ${entity}`}
			description={detail}
		>
			<Button
				type="button"
				className="min-h-11"
				variant="outline"
				asChild
			>
				<Link to={returnPath}>
					<ArrowLeft aria-hidden="true" className="size-4" />
					Back
				</Link>
			</Button>
			<Button
				type="button"
				className="min-h-11"
				onClick={() => window.location.reload()}
			>
				<RefreshCw aria-hidden="true" className="size-4" />
				Try again
			</Button>
		</RouteUnavailableState>
	);
}
