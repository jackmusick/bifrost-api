import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function AuditPagination({
	count,
	page,
	hasNext,
	pending,
	onPrevious,
	onNext,
}: {
	count: number;
	page: number;
	hasNext: boolean;
	pending: boolean;
	onPrevious: () => void;
	onNext: () => void;
}) {
	return (
		<nav
			aria-label="Audit pagination"
			className="flex flex-wrap items-center justify-between gap-3 py-4"
		>
			<p className="text-sm text-muted-foreground">
				{count} event{count !== 1 ? "s" : ""} on this page · Page{" "}
				{page + 1}
			</p>
			<div className="flex gap-2">
				<Button
					variant="outline"
					className="min-h-11"
					disabled={page === 0 || pending}
					onClick={onPrevious}
				>
					<ChevronLeft className="size-4" aria-hidden="true" />
					Previous
				</Button>
				<Button
					variant="outline"
					className="min-h-11"
					disabled={!hasNext || pending}
					onClick={onNext}
				>
					Next
					<ChevronRight className="size-4" aria-hidden="true" />
				</Button>
			</div>
		</nav>
	);
}
