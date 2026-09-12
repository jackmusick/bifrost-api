// client/src/components/editor/EditorOverlay.tsx

import { useRef } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { useEditorStore } from "@/stores/editorStore";
import { useAuth } from "@/contexts/AuthContext";
import { EditorLayout } from "./EditorLayout";
import { WindowOverlay } from "@/components/window-management";

/**
 * Editor overlay component
 * Renders the editor as a fullscreen overlay on top of the current page
 * Only visible when isOpen is true and user is a platform admin
 * When minimized, returns null - the unified dock handles the minimized state
 */
export function EditorOverlay() {
	const isOpen = useEditorStore((state) => state.isOpen);
	const layoutMode = useEditorStore((state) => state.layoutMode);
	const { isPlatformAdmin } = useAuth();
	const openerRef = useRef<HTMLElement | null>(null);

	if (!isOpen || !isPlatformAdmin) {
		return null;
	}

	// If minimized, don't render - unified dock handles this
	if (layoutMode === "minimized") {
		return null;
	}

	return (
		<DialogPrimitive.Root open>
			<DialogPrimitive.Content
				aria-describedby={undefined}
				className="absolute inset-0 outline-none"
				onOpenAutoFocus={() => {
					openerRef.current =
						document.activeElement instanceof HTMLElement
							? document.activeElement
							: null;
				}}
				onCloseAutoFocus={(event) => {
					event.preventDefault();
					const minimized =
						useEditorStore.getState().layoutMode === "minimized";
					const target = minimized
						? document.querySelector<HTMLElement>(
								'[data-window-id="editor"]',
							)
						: openerRef.current?.isConnected &&
							  openerRef.current !== document.body &&
							  !openerRef.current.hasAttribute("data-window-id")
							? openerRef.current
							: document.querySelector<HTMLElement>(
									"[data-editor-launcher]",
								);
					target?.focus();
				}}
				onEscapeKeyDown={(event) => event.preventDefault()}
				onInteractOutside={(event) => event.preventDefault()}
			>
				<DialogPrimitive.Title className="sr-only">
					Code editor
				</DialogPrimitive.Title>
				<WindowOverlay>
					<EditorLayout />
				</WindowOverlay>
			</DialogPrimitive.Content>
		</DialogPrimitive.Root>
	);
}
