import { useId, useState, type ReactNode } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Compact filters keep search and the document list in view on narrow screens. */
export function KnowledgeFilters({
	compact,
	activeCount,
	search,
	children,
}: {
	compact: boolean;
	activeCount: number;
	search: ReactNode;
	children: ReactNode;
}) {
	const [open, setOpen] = useState(false);
	const id = useId();
	if (!compact)
		return (
			<>
				{search}
				{children}
			</>
		);
	return (
		<div className="w-full min-w-0 space-y-3 p-3">
			<div className="flex min-w-0 items-center gap-2">
				<div className="min-w-0 flex-1">{search}</div>
				<Button
					variant="outline"
					className="min-h-11 shrink-0"
					aria-expanded={open}
					aria-controls={id}
					onClick={() => setOpen(!open)}
				>
					<SlidersHorizontal aria-hidden="true" className="size-4" />
					Filters{activeCount > 0 ? ` (${activeCount})` : ""}
				</Button>
			</div>
			<div id={id} hidden={!open} className="space-y-3">
				{children}
			</div>
		</div>
	);
}
