import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { EntityListToolbar } from "./EntityListToolbar";

it("exposes search, visible selection, explicit sort choices and busy status", async () => {
	const user = userEvent.setup();
	const props = {
		search: "Invoice",
		onSearch: vi.fn(),
		allSelected: false,
		someSelected: true,
		onSelectAll: vi.fn(),
		visibleCount: 2,
		selectedCount: 3,
		hiddenSelectedCount: 2,
		onClearSelection: vi.fn(),
		onDelete: vi.fn(),
		onEditSelection: vi.fn(),
		busy: false,
		busyMessage: "Updating…",
		sortBy: "name" as const,
		onSortBy: vi.fn(),
		ascending: true,
		onToggleDirection: vi.fn(),
	};
	const { rerender } = render(<EntityListToolbar {...props} />);
	expect(screen.getByRole("checkbox")).toHaveAttribute(
		"aria-checked",
		"mixed",
	);
	expect(screen.getByRole("checkbox").closest("label")).toHaveClass(
		"size-11",
	);
	expect(screen.queryByRole("status")).not.toBeInTheDocument();
	await user.click(screen.getByRole("checkbox").closest("label")!);
	expect(props.onSelectAll).toHaveBeenCalledOnce();
	expect(props.onSelectAll).toHaveBeenCalledWith(true);
	await user.click(screen.getByRole("combobox", { name: "Sort by" }));
	await user.click(screen.getByRole("option", { name: "Date" }));
	expect(props.onSortBy).toHaveBeenCalledWith("date");
	await user.click(screen.getByRole("button", { name: "Sort descending" }));
	expect(props.onToggleDirection).toHaveBeenCalledOnce();
	await user.click(screen.getByRole("button", { name: "Clear search" }));
	expect(props.onSearch).toHaveBeenCalledWith("");
	expect(
		screen.getByRole("textbox", { name: "Search entities" }),
	).toHaveFocus();
	rerender(<EntityListToolbar {...props} busy />);
	expect(screen.getByRole("checkbox")).toBeDisabled();
	expect(screen.getByRole("status")).toHaveTextContent("Updating…");
});
