import { useEditorStore } from "@/stores/editorStore";
import { useAuth } from "@/hooks/useAuth";
import { EditorLayout } from "./EditorLayout";

/**
 * Editor overlay component
 * Renders the editor as a fullscreen overlay on top of the current page
 * Only visible when isOpen is true and user is a platform admin
 * When minimized, only shows the docked button without the fullscreen background
 */
export function EditorOverlay() {
	const isOpen = useEditorStore((state) => state.isOpen);
	const layoutMode = useEditorStore((state) => state.layoutMode);
	const { user } = useAuth();

	// Check if user is platform admin
	const isPlatformAdmin = user?.userRoles?.includes("PlatformAdmin") ?? false;

	if (!isOpen || !isPlatformAdmin) {
		return null;
	}

	// If minimized, don't render the fullscreen background
	if (layoutMode === "minimized") {
		return <EditorLayout />;
	}

	return (
		<div className="fixed inset-0 z-50 bg-background">
			<EditorLayout />
		</div>
	);
}
