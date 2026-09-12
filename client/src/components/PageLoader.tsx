import { Loader2 } from "lucide-react";

interface PageLoaderProps {
	message?: string;
	size?: "sm" | "md" | "lg";
	fullScreen?: boolean;
}

export function PageLoader({
	message = "Loading...",
	size = "md",
	fullScreen = false,
}: PageLoaderProps) {
	const sizeClasses = {
		sm: "h-8 w-8",
		md: "h-12 w-12",
		lg: "h-16 w-16",
	};

	const containerClasses = fullScreen
		? "flex h-[100dvh] w-full items-center justify-center bg-background px-4 py-8"
		: "flex h-full min-h-[400px] w-full items-center justify-center px-4 py-8";

	return (
		<div
			className={containerClasses}
			role="status"
			aria-live="polite"
			aria-label={message}
		>
			<div className="flex max-w-xs flex-col items-center gap-4 text-center">
				<Loader2
					aria-hidden="true"
					className={`${sizeClasses[size]} animate-spin text-primary motion-reduce:animate-none`}
				/>
				<p className="text-balance text-sm text-muted-foreground [overflow-wrap:anywhere]">
					{message}
				</p>
			</div>
		</div>
	);
}
