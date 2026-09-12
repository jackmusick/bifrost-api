import { cn } from "@/lib/utils";

/** Shared selection treatment for primary and workspace navigation. */
export function navigationSelectionClasses(active: boolean) {
	return cn(
		"rounded-none border-l-2 hover:bg-accent hover:text-accent-foreground",
		active
			? "border-primary bg-primary/[0.07] text-primary"
			: "border-transparent text-muted-foreground",
	);
}
