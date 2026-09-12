import * as React from "react";
import {
	ChevronLeftIcon,
	ChevronRightIcon,
	MoreHorizontalIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";

function Pagination({ className, ...props }: React.ComponentProps<"nav">) {
	return (
		<nav
			role="navigation"
			aria-label="pagination"
			data-slot="pagination"
			className={cn(
				"mx-auto flex min-w-0 w-full justify-center",
				className,
			)}
			{...props}
		/>
	);
}

function PaginationContent({
	className,
	...props
}: React.ComponentProps<"ul">) {
	return (
		<ul
			data-slot="pagination-content"
			className={cn(
				"flex min-w-0 flex-row flex-wrap items-center justify-center gap-1",
				className,
			)}
			{...props}
		/>
	);
}

function PaginationItem({ ...props }: React.ComponentProps<"li">) {
	return <li data-slot="pagination-item" {...props} />;
}

type PaginationLinkProps = {
	isActive?: boolean;
} & Pick<React.ComponentProps<typeof Button>, "size"> &
	React.ComponentProps<"a">;

function PaginationLink({
	className,
	isActive,
	size = "icon",
	href,
	onClick,
	onKeyDown,
	tabIndex,
	"aria-disabled": ariaDisabled,
	...props
}: PaginationLinkProps) {
	const disabled = ariaDisabled === true || ariaDisabled === "true";
	const action = !href && !!onClick;
	return (
		<a
			href={href}
			role={action ? "button" : undefined}
			tabIndex={disabled ? -1 : (tabIndex ?? (action ? 0 : undefined))}
			aria-disabled={ariaDisabled}
			onClick={(event) => {
				if (disabled) {
					event.preventDefault();
					return;
				}
				onClick?.(event);
			}}
			onKeyDown={(event) => {
				onKeyDown?.(event);
				if (
					!event.defaultPrevented &&
					!disabled &&
					action &&
					(event.key === "Enter" || event.key === " ")
				) {
					event.preventDefault();
					event.currentTarget.click();
				}
			}}
			aria-current={isActive ? "page" : undefined}
			data-slot="pagination-link"
			data-active={isActive}
			className={cn(
				buttonVariants({
					variant: isActive ? "outline" : "ghost",
					size,
				}),
				"min-h-11 min-w-11 aria-disabled:opacity-50 aria-disabled:cursor-not-allowed",
				className,
			)}
			{...props}
		/>
	);
}

function PaginationPrevious({
	className,
	...props
}: React.ComponentProps<typeof PaginationLink>) {
	return (
		<PaginationLink
			aria-label="Go to previous page"
			size="default"
			className={cn("gap-1 px-2.5 sm:pl-2.5", className)}
			{...props}
		>
			<ChevronLeftIcon />
			<span className="hidden sm:block">Previous</span>
		</PaginationLink>
	);
}

function PaginationNext({
	className,
	...props
}: React.ComponentProps<typeof PaginationLink>) {
	return (
		<PaginationLink
			aria-label="Go to next page"
			size="default"
			className={cn("gap-1 px-2.5 sm:pr-2.5", className)}
			{...props}
		>
			<span className="hidden sm:block">Next</span>
			<ChevronRightIcon />
		</PaginationLink>
	);
}

function PaginationEllipsis({
	className,
	...props
}: React.ComponentProps<"span">) {
	return (
		<span
			aria-hidden
			data-slot="pagination-ellipsis"
			className={cn("flex size-9 items-center justify-center", className)}
			{...props}
		>
			<MoreHorizontalIcon className="size-4" />
			<span className="sr-only">More pages</span>
		</span>
	);
}

export {
	Pagination,
	PaginationContent,
	PaginationLink,
	PaginationItem,
	PaginationPrevious,
	PaginationNext,
	PaginationEllipsis,
};
