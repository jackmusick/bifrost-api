import { renderWithProviders, screen, within } from "@/test-utils";
import { expect, it, vi } from "vitest";
import { KnowledgeDocumentList } from "./KnowledgeDocumentList";

it("keeps scope and Markdown preview readable while separating open from bulk selection", async () => {
	const doc = {
		id: "doc-1",
		namespace: "support",
		key: "Runbook",
		content_preview: "# Getting started\n\nReview **access** first.",
		metadata: {},
		organization_id: "org-1",
		created_at: null,
	};
	const onOpen = vi.fn();
	const onToggleSelect = vi.fn();
	const props = {
		documents: [doc],
		selectedDocId: null,
		selectionMode: false,
		isPlatformAdmin: true,
		selectedIds: new Set<string>(),
		allVisibleSelected: false,
		getOrgName: () => "A long customer organization name",
		busy: false,
		onToggleSelect,
		onToggleSelectAll: vi.fn(),
		onOpen,
		onDelete: vi.fn(),
	};
	const { user, rerender } = renderWithProviders(
		<KnowledgeDocumentList {...props} />,
	);
	const row = screen.getByRole("article", { name: "Runbook" });
	expect(
		within(row).getByText("A long customer organization name"),
	).toBeVisible();
	expect(row).toHaveTextContent("Getting started");
	expect(row).not.toHaveTextContent("# Getting started");
	await user.click(screen.getByRole("button", { name: "Runbook" }));
	expect(onOpen).toHaveBeenCalledWith(doc);
	rerender(<KnowledgeDocumentList {...props} selectionMode />);
	expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Runbook" }));
	expect(onToggleSelect).toHaveBeenCalledWith("doc-1");
	expect(onOpen).toHaveBeenCalledTimes(1);
});
