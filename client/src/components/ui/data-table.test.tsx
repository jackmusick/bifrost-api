import type * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, renderWithProviders, screen } from "@/test-utils";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableFooter,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "./data-table";

function renderClickableRow({
	onClick,
	onMouseUp,
	href,
}: {
	onClick?: React.MouseEventHandler<HTMLTableRowElement>;
	onMouseUp?: React.MouseEventHandler<HTMLTableRowElement>;
	href?: string;
} = {}) {
	const rowClick =
		onClick ?? vi.fn<React.MouseEventHandler<HTMLTableRowElement>>();

	renderWithProviders(
		<DataTable>
			<DataTableBody>
				<DataTableRow
					clickable
					href={href}
					onClick={rowClick}
					onMouseUp={onMouseUp}
				>
					<DataTableCell>Plain cell</DataTableCell>
					<DataTableCell>
						<a href="/nested-link">Nested link</a>
						<button type="button">Nested button</button>
						<input type="checkbox" aria-label="Nested checkbox" />
					</DataTableCell>
				</DataTableRow>
			</DataTableBody>
		</DataTable>,
	);

	return {
		onClick: rowClick,
		onMouseUp,
		row: screen.getByRole("row", { name: /plain cell/i }),
	};
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("DataTableRow row action guard", () => {
	it("opens from a plain cell click", () => {
		const { onClick } = renderClickableRow();

		fireEvent.click(screen.getByText("Plain cell"));

		expect(onClick).toHaveBeenCalledTimes(1);
	});

	it("lets nested link, button, and checkbox controls act independently", () => {
		const { onClick } = renderClickableRow();
		const link = screen.getByRole("link", { name: "Nested link" });
		const button = screen.getByRole("button", { name: "Nested button" });
		const checkbox = screen.getByRole("checkbox", {
			name: "Nested checkbox",
		});

		fireEvent.click(link);
		fireEvent.click(button);
		fireEvent.click(checkbox);

		expect(onClick).not.toHaveBeenCalled();
		expect(checkbox).toBeChecked();
	});

	it("opens an href exactly once for ctrl-click", () => {
		const open = vi.spyOn(window, "open").mockImplementation(() => null);
		const { onClick } = renderClickableRow({
			href: "/records/123",
		});

		fireEvent.click(screen.getByText("Plain cell"), { ctrlKey: true });

		expect(open).toHaveBeenCalledTimes(1);
		expect(open).toHaveBeenCalledWith("/records/123", "_blank");
		expect(onClick).not.toHaveBeenCalled();
	});

	it("opens an href exactly once for middle-click and preserves caller mouseup", () => {
		const open = vi.spyOn(window, "open").mockImplementation(() => null);
		const onMouseUp = vi.fn();
		const { onClick, row } = renderClickableRow({
			href: "/records/123",
			onMouseUp,
		});

		fireEvent.mouseUp(screen.getByText("Plain cell"), { button: 1 });
		fireEvent.click(row, { button: 1 });

		expect(open).toHaveBeenCalledTimes(1);
		expect(open).toHaveBeenCalledWith("/records/123", "_blank");
		expect(onMouseUp).not.toHaveBeenCalled();
		expect(onClick).not.toHaveBeenCalled();
	});

	it("still calls caller mouseup for ordinary mouseup events", () => {
		const onMouseUp = vi.fn();
		renderClickableRow({ href: "/records/123", onMouseUp });

		fireEvent.mouseUp(screen.getByText("Plain cell"), { button: 0 });

		expect(onMouseUp).toHaveBeenCalledTimes(1);
	});

	it("does not open the row while selected text is active inside it", () => {
		const { onClick, row } = renderClickableRow();
		const selection = {
			anchorNode: row.firstChild,
			isCollapsed: false,
		} as Selection;
		vi.spyOn(window, "getSelection").mockReturnValue(selection);

		fireEvent.click(screen.getByText("Plain cell"));

		expect(onClick).not.toHaveBeenCalled();
	});
});

describe("DataTable footer placement", () => {
	it("keeps the footer outside the scrollable table body", () => {
		renderWithProviders(
			<DataTable aria-label="Records">
				<DataTableHeader>
					<DataTableRow>
						<DataTableHead>Name</DataTableHead>
					</DataTableRow>
				</DataTableHeader>
				<DataTableBody>
					<DataTableRow>
						<DataTableCell>Visible row</DataTableCell>
					</DataTableRow>
				</DataTableBody>
				<DataTableFooter>
					<DataTableRow>
						<DataTableCell>Persistent footer</DataTableCell>
					</DataTableRow>
				</DataTableFooter>
			</DataTable>,
		);

		const root = screen.getByLabelText("Records");
		const scrollBody = root.firstElementChild;
		const footerShell = root.lastElementChild;

		expect(scrollBody).not.toBe(footerShell);
		expect(scrollBody).toHaveClass("overflow-auto");
		expect(scrollBody).toHaveTextContent("Visible row");
		expect(scrollBody).not.toHaveTextContent("Persistent footer");
		expect(footerShell).toHaveTextContent("Persistent footer");
	});
});
