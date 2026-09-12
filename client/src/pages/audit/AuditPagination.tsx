import { PaginationFooter } from "@/components/pagination/PaginationFooter";

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
		<PaginationFooter
			aria-label="Audit pagination"
			summary={`${count} event${count !== 1 ? "s" : ""} on this page · Page ${page + 1}`}
			pending={pending}
			previousDisabled={page === 0 || pending}
			nextDisabled={!hasNext || pending}
			onPrevious={onPrevious}
			onNext={onNext}
		/>
	);
}
