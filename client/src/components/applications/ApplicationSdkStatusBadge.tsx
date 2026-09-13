import {
	AlertTriangle,
	CheckCircle2,
	Clock3,
	HelpCircle,
	Loader2,
	RefreshCw,
	XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/v1";

type ApplicationSdkStatus =
	components["schemas"]["ApplicationPublic"]["sdk_status"];

export type ApplicationSdkUpdateState =
	| "idle"
	| "queued"
	| "updating"
	| "failed";

type SdkStatusInput = {
	sdk_status: ApplicationSdkStatus;
	sdk_source_available: boolean;
};

export function canUpdateApplicationSdk(
	app: SdkStatusInput,
	updateState: ApplicationSdkUpdateState = "idle",
): boolean {
	if (updateState === "queued" || updateState === "updating") return false;
	if (!app.sdk_source_available) return false;
	if (updateState === "failed") return true;
	return (
		(app.sdk_status === "update_available" ||
			app.sdk_status === "update_required" ||
			app.sdk_status === "unknown")
	);
}

function sdkStatusPresentation(
	status: ApplicationSdkStatus,
	updateState: ApplicationSdkUpdateState,
) {
	if (updateState === "queued") {
		return {
			label: "SDK update queued",
			icon: Clock3,
			className:
				"border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300",
		};
	}
	if (updateState === "updating") {
		return {
			label: "Updating SDK",
			icon: Loader2,
			className:
				"border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300",
			spin: true,
		};
	}
	if (updateState === "failed") {
		return {
			label: "SDK update failed",
			icon: XCircle,
			className:
				"border-destructive/30 bg-destructive/10 text-destructive",
		};
	}
	switch (status) {
		case "current":
			return {
				label: "SDK current",
				icon: CheckCircle2,
				className:
					"border-[var(--bf-success)]/25 bg-[var(--bf-success)]/10 text-[var(--bf-success)]",
			};
		case "update_available":
			return {
				label: "SDK update available",
				icon: RefreshCw,
				className:
					"border-[var(--bf-warning)]/30 bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]",
			};
		case "update_required":
			return {
				label: "SDK update required",
				icon: AlertTriangle,
				className:
					"border-destructive/30 bg-destructive/10 text-destructive",
			};
		case "unknown":
		default:
			return {
				label: "SDK unknown",
				icon: HelpCircle,
				className:
					"border-muted-foreground/30 bg-muted text-muted-foreground",
			};
	}
}

export function ApplicationSdkStatusBadge({
	status,
	updateState = "idle",
	showCurrent = false,
	className,
}: {
	status: ApplicationSdkStatus;
	updateState?: ApplicationSdkUpdateState;
	showCurrent?: boolean;
	className?: string;
}) {
	if (status === "not_applicable") return null;
	if (status === "current" && !showCurrent) return null;
	const presentation = sdkStatusPresentation(status, updateState);
	const Icon = presentation.icon;

	return (
		<Badge
			variant="outline"
			aria-label={presentation.label}
			className={cn(
				"gap-1 whitespace-nowrap text-xs",
				presentation.className,
				className,
			)}
		>
			<Icon
				aria-hidden="true"
				className={cn(
					"h-3 w-3",
					presentation.spin && "animate-spin motion-reduce:animate-none",
				)}
			/>
			{presentation.label}
		</Badge>
	);
}
