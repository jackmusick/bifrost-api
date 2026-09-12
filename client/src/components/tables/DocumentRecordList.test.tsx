import { describe, it, expect, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { DocumentRecordList } from "./DocumentRecordList";
import type { DocumentPublic } from "@/services/tables";

const doc = {
	id: "record-1",
	table_id: "table-1",
	updated_at: null,
	created_by: null,
	updated_by: null,
	data: { name: "**Customer**", config: { enabled: true } },
	created_at: "2026-09-11T00:00:00Z",
} as DocumentPublic;
describe("DocumentRecordList", () => {
	it("opens a record without expanding raw JSON and renders Markdown summaries", async () => {
		const onOpen = vi.fn();
		const { user } = await renderWithProviders(
			<DocumentRecordList
				documents={[doc]}
				dataColumns={["name", "config"]}
				onOpen={onOpen}
				onEdit={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);
		expect(screen.queryByText("View full JSON")).not.toBeInTheDocument();
		expect(screen.queryByText("**Customer**")).not.toBeInTheDocument();
		expect(screen.getAllByText("Customer").length).toBeGreaterThan(0);
		await user.click(
			screen.getByRole("button", { name: "Open document record-1" }),
		);
		expect(onOpen).toHaveBeenCalledWith(doc);
	});
	it("keeps record actions separate from opening the inspector", async () => {
		const onOpen = vi.fn(),
			onEdit = vi.fn();
		const { user } = await renderWithProviders(
			<DocumentRecordList
				documents={[doc]}
				dataColumns={["name"]}
				onOpen={onOpen}
				onEdit={onEdit}
				onDelete={vi.fn()}
			/>,
		);
		await user.click(
			screen.getAllByRole("button", {
				name: "Document record-1 actions",
			})[0],
		);
		await user.click(screen.getByRole("menuitem", { name: "Edit" }));
		expect(onEdit).toHaveBeenCalledWith(doc);
		expect(onOpen).not.toHaveBeenCalled();
	});
});
