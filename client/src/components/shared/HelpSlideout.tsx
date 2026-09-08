/**
 * Shared help slide-out: a HelpCircle icon button that opens a right-side
 * sheet rendering arbitrary reference content. Extracted from the
 * PolicyReferencePanel so future schema-driven editors (Custom Claims, etc.)
 * can reuse the same chrome.
 *
 * The component is self-contained — it owns the open/close state and the
 * trigger. Consumers just pass a title and children (the body content).
 */

import { useState, useRef, type ReactNode } from "react";
import { HelpCircle } from "lucide-react";
import {
	Sheet,
	SheetContent,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface HelpSlideoutProps {
	title: string;
	children: ReactNode;
	/** Optional className for the trigger button (icon size, etc.). */
	triggerClassName?: string;
}

export function HelpSlideout({
	title,
	children,
	triggerClassName,
}: HelpSlideoutProps) {
	const [open, setOpen] = useState(false);
	const contentRef = useRef<HTMLDivElement>(null);
	return (
		<Sheet open={open} onOpenChange={setOpen}>
			<SheetTrigger asChild>
				<Button
					type="button"
					variant="ghost"
					size="sm"
					aria-label={title}
					className={cn(
						"h-11 w-11 p-0 sm:h-8 sm:w-8",
						triggerClassName,
					)}
				>
					<HelpCircle className="h-4 w-4" />
				</Button>
			</SheetTrigger>
			<SheetContent
				ref={contentRef}
				onOpenAutoFocus={(event) => {
					event.preventDefault();
					contentRef.current?.focus({ preventScroll: true });
					if (contentRef.current) contentRef.current.scrollTop = 0;
				}}
				side="right"
				className="w-[420px] sm:w-[480px] sm:max-w-[480px] overflow-hidden"
				aria-label={title}
			>
				<SheetHeader className="border-b">
					<SheetTitle>{title}</SheetTitle>
				</SheetHeader>
				<div role="region" aria-label={`${title} content`} className="min-h-0 min-w-0 flex-1 space-y-6 overflow-y-auto px-6 py-6 [overflow-wrap:anywhere]">
					{children}
				</div>
			</SheetContent>
		</Sheet>
	);
}
