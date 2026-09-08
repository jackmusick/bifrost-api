import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ListToolbarProps {
	children: ReactNode;
	className?: string;
}

export function ListToolbar({ children, className }: ListToolbarProps) {
	return (
		<div
			className={cn(
				"flex min-w-0 max-w-full flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center",
				className,
			)}
		>
			{children}
		</div>
	);
}
