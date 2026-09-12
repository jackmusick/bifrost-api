import { useRef, type RefObject } from "react";

/** Restore the opener for controlled dialogs without a Radix DialogTrigger. */
export function useDialogReturnFocus(fallback?: RefObject<HTMLElement | null>, preferFallback = false) {
	const opener = useRef<HTMLElement | null>(null);
	return {
		onOpenAutoFocus: () => {
			opener.current = document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;
		},
		onCloseAutoFocus: (event: Event) => {
			const target = preferFallback ? fallback?.current : (opener.current?.isConnected ? opener.current : fallback?.current);
			if (target?.isConnected) {
				event.preventDefault();
				target.focus({ preventScroll: true });
			}
			opener.current = null;
		},
	};
}
