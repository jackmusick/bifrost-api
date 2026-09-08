import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

interface Props {
	page: number;
	pageSize: number;
	total: number;
	busy: boolean;
	onPageChange: (page: number) => void;
	onPageSizeChange: (size: number) => void;
}

export function DocumentPagination({
	page,
	pageSize,
	total,
	busy,
	onPageChange,
	onPageSizeChange,
}: Props) {
	const pages = Math.max(1, Math.ceil(total / pageSize));
	return (
		<footer className="flex flex-wrap items-center justify-between gap-4 border-t pt-4 text-sm">
			<div className="flex flex-wrap items-center gap-3">
				<p role="status" className="text-muted-foreground">
					{total === 0 || page * pageSize >= total
						? 0
						: page * pageSize + 1}
					–{Math.min((page + 1) * pageSize, total)} of {total}{" "}
					documents
				</p>
				<Select
					value={String(pageSize)}
					onValueChange={(value) => onPageSizeChange(Number(value))}
					disabled={busy}
				>
					<SelectTrigger
						aria-label="Documents per page"
						className="min-h-11 w-20"
					>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{[10, 25, 50, 100].map((size) => (
							<SelectItem
								key={size}
								value={String(size)}
								className="min-h-11"
							>
								{size}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				<span className="text-muted-foreground">per page</span>
			</div>
			<nav
				aria-label="Document pages"
				className="flex w-full items-center justify-between gap-3 sm:w-auto"
			>
				<Button
					type="button"
					variant="outline"
					size="icon-lg"
					aria-label="Previous page"
					disabled={busy || page === 0}
					onClick={() => onPageChange(Math.max(0, page - 1))}
				>
					<ChevronLeft aria-hidden="true" className="size-4" />
				</Button>
				<span className="tabular-nums">
					Page {page + 1} of {Math.max(pages, page + 1)}
				</span>
				<Button
					type="button"
					variant="outline"
					size="icon-lg"
					aria-label="Next page"
					disabled={busy || page >= pages - 1}
					onClick={() => onPageChange(page + 1)}
				>
					<ChevronRight aria-hidden="true" className="size-4" />
				</Button>
			</nav>
		</footer>
	);
}
