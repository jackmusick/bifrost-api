import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { useVersionCheck } from "@/hooks/useVersionCheck";

/**
 * Compact "new version available" affordance for the app header.
 *
 * Polls /api/version via useVersionCheck; renders nothing until a version
 * mismatch is detected, then surfaces a small icon button with a primary
 * status dot. Click reloads the page; tooltip explains.
 */
export function VersionUpdateBanner() {
	const updateAvailable = useVersionCheck();
	if (!updateAvailable) return null;

	return (
		<div>
			<span role="status" className="sr-only">
				A new version of Bifrost is available.
			</span>
			<TooltipProvider delayDuration={150}>
				<Tooltip>
					<TooltipTrigger asChild>
						<Button
							type="button"
							aria-label="Update available — click to refresh"
							variant="ghost"
							size="icon"
							onClick={() => window.location.reload()}
							className="relative size-11 text-primary hover:text-primary"
						>
							<RefreshCw className="h-4 w-4" />
							<span
								aria-hidden="true"
								className="absolute top-1 right-1 h-2.5 w-2.5 rounded-full bg-primary ring-2 ring-background"
							/>
						</Button>
					</TooltipTrigger>
					<TooltipContent
						side="bottom"
						collisionPadding={16}
						className="max-w-[min(20rem,calc(100vw-2rem))]"
					>
						A new version of Bifrost is available. Click to refresh.
					</TooltipContent>
				</Tooltip>
			</TooltipProvider>
		</div>
	);
}
