import { describe, expect, it } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { MarkdownContent } from "./MarkdownContent";

describe("MarkdownContent", () => {
	it("renders field headings, lists, tables and code without document-sized headings", () => {
		const { container } = renderWithProviders(
			<MarkdownContent
				content={
					'# Outcome\n\n### Checks\n\n- **Passed**\n- `customer_id`\n\n| Field | Value |\n| --- | --- |\n| Status | Ready |\n\n```json\n{"ok":true}\n```'
				}
			/>,
		);
		expect(
			screen.getByRole("heading", { name: "Outcome", level: 4 }),
		).toBeInTheDocument();
		expect(screen.getByRole("heading", { name: "Checks" })).toHaveClass(
			"text-[1em]",
		);
		expect(screen.getAllByRole("listitem")).toHaveLength(2);
		expect(screen.getByRole("cell", { name: "Ready" })).toBeInTheDocument();
		expect(container.querySelector("pre code")).toHaveTextContent(
			'{"ok":true}',
		);
	});
	it("keeps previews inline and noninteractive within a clickable row", () => {
		const { container } = renderWithProviders(
			<button>
				<MarkdownContent
					variant="preview"
					content={
						"### Result\n\nA **good** [result](https://example.com).\n\n- First\n- Second\n\n| Key | Value |\n| --- | --- |\n| Ready | Yes |"
					}
				/>
			</button>,
		);
		expect(screen.getByRole("button")).toHaveTextContent(
			"Result A good result. First Second Key Value Ready Yes",
		);
		expect(container.querySelector("p,div h1,h4,ul,table,a")).toBeNull();
		expect(screen.queryByRole("link")).not.toBeInTheDocument();
	});
	it("does not execute raw HTML, unsafe links, or fetch embedded images", () => {
		const { container } = renderWithProviders(
			<MarkdownContent
				content={
					"<script>alert(1)</script>\n\n[Unsafe](javascript:alert%281%29)\n\n![Screenshot](https://example.com/tracker.png)"
				}
			/>,
		);
		expect(container.querySelector("script,img")).toBeNull();
		expect(screen.getByText("Unsafe")).not.toHaveAttribute(
			"href",
			expect.stringContaining("javascript:"),
		);
		expect(screen.getByText("Screenshot")).toBeInTheDocument();
	});
});
