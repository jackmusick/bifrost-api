import type { ComponentProps } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** The primary action forms the trailing edge of a contained workspace toolbar. */
export function WorkspacePrimaryAction({
	className,
	...props
}: ComponentProps<typeof Button>) {
	return (
		<Button
			{...props}
			className={cn(
				"ml-auto h-auto min-h-12 self-stretch rounded-none border-0 px-4 sm:px-5 shadow-none focus-visible:ring-inset active:not-aria-[haspopup]:translate-y-0",
				className,
			)}
		/>
	);
}
