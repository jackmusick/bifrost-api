import { fileService } from "@/services/fileService";
import { useEditorStore, type EditorTab } from "@/stores/editorStore";

type Conflict = NonNullable<EditorTab["gitConflict"]>;

/** Resolve the reviewed conflict without letting an asynchronous save target another tab. */
export async function resolveEditorConflict(
	path: string,
	conflict: Conflict,
	choice: "current" | "incoming",
) {
	const original = useEditorStore
		.getState()
		.tabs.find(
			(tab) => tab.file.path === path && tab.gitConflict === conflict,
		);
	if (!original) throw new Error("This conflict is no longer available.");
	const content =
		choice === "current"
			? conflict.current_content
			: conflict.incoming_content;
	const result = await fileService.writeFile(
		path,
		content,
		"utf-8",
		conflict.current_etag,
	);
	useEditorStore.setState((state) => ({
		tabs: state.tabs.map((tab) => {
			if (tab.file.path !== path || tab.gitConflict !== conflict)
				return tab;
			const editedDuringSave = tab.content !== original.content;
			const resolved = { ...tab };
			delete resolved.gitConflict;
			delete resolved.conflictReason;
			return {
				...resolved,
				content: editedDuringSave
					? tab.content
					: result.content_modified
						? result.content
						: content,
				etag: result.etag ?? tab.etag,
				unsavedChanges: editedDuringSave,
				saveState: editedDuringSave
					? ("dirty" as const)
					: ("saved" as const),
				serverContentDiffers: false,
			};
		}),
	}));
}
