import { useEffect, useRef } from "react";

export function TuningActionError({ message }: { message: string }) {
	const ref = useRef<HTMLParagraphElement>(null);
	useEffect(() => {
		ref.current?.focus();
		ref.current?.scrollIntoView?.({ block: "nearest" });
	}, [message]);
	return (
		<p
			ref={ref}
			tabIndex={-1}
			role="alert"
			className="rounded-[var(--bf-radius-control)] border bg-[var(--bf-warning-soft)] p-3 text-sm"
		>
			{message}
		</p>
	);
}
