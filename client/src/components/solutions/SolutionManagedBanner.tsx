/**
 * SolutionManagedBanner
 *
 * Shown at the top of an entity editor when the entity is managed by a deployed
 * Solution (`is_solution_managed`). Solution-managed entities are read-only on
 * the platform — the single writer is deployment (success-criteria §3.2,
 * criterion 6). Editors render this banner and disable their save/delete
 * controls; the API rejects the mutation regardless, so this is purely the
 * read-only *affordance*.
 */

import { Lock } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export interface SolutionManagedBannerProps {
	/** Entity noun for the message, e.g. "workflow", "form", "agent". */
	entityLabel?: string;
}

export function SolutionManagedBanner({
	entityLabel = "entity",
}: SolutionManagedBannerProps) {
	return (
		<Alert
			data-testid="solution-managed-banner"
			className="items-start rounded-[var(--bf-radius-surface)] border-[color:var(--bf-info-soft)] bg-[color:var(--bf-info-soft)]/20"
		>
			<Lock aria-hidden="true" className="size-4 text-[var(--bf-info)]" />
			<AlertTitle>Managed by a Solution</AlertTitle>
			<AlertDescription>
				This {entityLabel} is read-only here. Re-deploy the Solution to make
				changes on the platform.
			</AlertDescription>
		</Alert>
	);
}

export default SolutionManagedBanner;
