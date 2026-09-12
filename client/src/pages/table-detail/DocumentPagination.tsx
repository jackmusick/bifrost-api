import { PaginationFooter } from "@/components/pagination/PaginationFooter";
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
	const first =
		total === 0 || page * pageSize >= total ? 0 : page * pageSize + 1;
	const last = Math.min((page + 1) * pageSize, total);
	return (
		<footer className="shrink-0 border-t bg-muted/10 px-4">
			<PaginationFooter
				aria-label="Document pages"
				className="gap-3 py-3"
				summary={
					<span className="flex flex-wrap items-center gap-3">
						<span role="status" className="text-muted-foreground">
							{first}–{last} of {total} documents · Page{" "}
							{page + 1} of {Math.max(pages, page + 1)}
						</span>
						<Select
							value={String(pageSize)}
							onValueChange={(value) =>
								onPageSizeChange(Number(value))
							}
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
					</span>
				}
				pending={busy}
				showControls={pages > 1 || page > 0}
				previousDisabled={busy || page === 0}
				nextDisabled={busy || page >= pages - 1}
				onPrevious={() => onPageChange(Math.max(0, page - 1))}
				onNext={() => onPageChange(page + 1)}
			/>
		</footer>
	);
}
