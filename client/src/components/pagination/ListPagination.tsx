import { PaginationFooter } from "./PaginationFooter";

interface ListPaginationProps {
	offset: number;
	limit: number;
	total: number;
	isFetching?: boolean;
	onPageChange: (offset: number) => void;
}

export function ListPagination({
	offset,
	limit,
	total,
	isFetching = false,
	onPageChange,
}: ListPaginationProps) {
	const page = Math.floor(offset / limit);
	const totalPages = Math.max(1, Math.ceil(total / limit));
	const previousDisabled = page === 0 || isFetching;
	const nextDisabled = page + 1 >= totalPages || isFetching;
	const first = total === 0 ? 0 : offset + 1;
	const last = Math.min(offset + limit, total);
	const showControls = totalPages > 1 || page > 0;

	return (
		<PaginationFooter
			aria-label="List pagination"
			className="px-4 sm:px-6"
			summary={`${first}–${last} of ${total} · Page ${page + 1} of ${totalPages}`}
			pending={isFetching}
			showControls={showControls}
			previousDisabled={previousDisabled}
			nextDisabled={nextDisabled}
			onPrevious={() => onPageChange(Math.max(0, offset - limit))}
			onNext={() => onPageChange(offset + limit)}
		/>
	);
}
