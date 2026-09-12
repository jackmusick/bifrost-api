import { renderWithProviders, screen, fireEvent } from "@/test-utils";
import { expect, it, vi } from "vitest";
import { KnowledgeEditorPane } from "./KnowledgeEditorPane";
it("prevents closing a saving editor and restores Escape after saving", () => {
	const onClose = vi.fn();
	const { rerender } = renderWithProviders(
		<KnowledgeEditorPane open inline={false} busy onClose={onClose}>
			Content
		</KnowledgeEditorPane>,
	);
	fireEvent.keyDown(
		screen.getByRole("region", { name: "Knowledge document editor" }),
		{ key: "Escape" },
	);
	expect(onClose).not.toHaveBeenCalled();
	rerender(
		<KnowledgeEditorPane open inline={false} busy={false} onClose={onClose}>
			Content
		</KnowledgeEditorPane>,
	);
	fireEvent.keyDown(
		screen.getByRole("region", { name: "Knowledge document editor" }),
		{ key: "Escape" },
	);
	expect(onClose).toHaveBeenCalledOnce();
});
