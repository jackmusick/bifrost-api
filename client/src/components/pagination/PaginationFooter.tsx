import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

interface PaginationFooterProps {
	"aria-label": string;
	summary: ReactNode;
	previousDisabled: boolean;
	nextDisabled: boolean;
	pending?: boolean;
	showControls?: boolean;
	onPrevious: () => void;
	onNext: () => void;
	className?: string;
}

export function PaginationFooter({
	"aria-label": ariaLabel,
	summary,
	previousDisabled,
	nextDisabled,
	pending = false,
	showControls = true,
	onPrevious,
	onNext,
	className,
}: PaginationFooterProps) {
	return (
		<nav
			aria-label={ariaLabel}
			className={`flex shrink-0 flex-wrap items-center justify-between gap-3 py-4 ${className ?? ""}`}
		>
			<div className="flex items-center gap-1.5 text-sm text-muted-foreground">
				{pending ? (
					<Loader2
						className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none"
						aria-label="Loading page"
					/>
				) : null}
				<span aria-live="polite">{summary}</span>
			</div>
			{showControls && (
				<div className="flex gap-2">
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						disabled={previousDisabled}
						onClick={onPrevious}
					>
						<ChevronLeft className="size-4" aria-hidden="true" />
						Previous
					</Button>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						disabled={nextDisabled}
						onClick={onNext}
					>
						Next
						<ChevronRight className="size-4" aria-hidden="true" />
					</Button>
				</div>
			)}
		</nav>
	);
}
