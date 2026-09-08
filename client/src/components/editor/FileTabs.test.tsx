import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FileTabs } from "./FileTabs";
import { useEditorSession } from "@/hooks/useEditorSession";
vi.mock("@/services/fileService", () => ({
	fileService: {
		readFile: vi.fn().mockResolvedValue({
			content: "pass",
			etag: "same",
			encoding: "utf-8",
		}),
	},
}));
vi.mock("@/hooks/useEditorSession", () => ({ useEditorSession: vi.fn() }));
vi.mock("@atlaskit/pragmatic-drag-and-drop/element/adapter", () => ({
	draggable: () => () => {},
	dropTargetForElements: () => () => {},
}));
const actions = {
	setActiveTab: vi.fn(),
	closeTab: vi.fn(),
	closeAllTabs: vi.fn(),
	closeOtherTabs: vi.fn(),
	openFileInTab: vi.fn(),
	setLoadingFile: vi.fn(),
	reorderTabs: vi.fn(),
	setConflictState: vi.fn(),
};
beforeEach(() => {
	vi.clearAllMocks();
	vi.mocked(useEditorSession).mockReturnValue({
		...actions,
		tabs: [
			{
				file: { name: "first.py", path: "folder/first.py" },
				content: "pass",
				etag: "same",
				unsavedChanges: false,
			},
			{
				file: { name: "second.py", path: "folder/second.py" },
				content: "pass",
				etag: "same",
				unsavedChanges: true,
			},
		],
		activeTabIndex: 0,
	} as unknown as ReturnType<typeof useEditorSession>);
});
describe("FileTabs", () => {
	it("selects a file with the keyboard and exposes full path and active state", async () => {
		const user = userEvent.setup();
		render(<FileTabs />);
		expect(
			screen.getByRole("button", { name: "Open folder/first.py" }),
		).toHaveAttribute("aria-pressed", "true");
		const second = screen.getByRole("button", {
			name: "Open folder/second.py",
		});
		second.focus();
		await user.keyboard("{Enter}");
		expect(actions.setActiveTab).toHaveBeenCalledWith(1);
	});
	it("closes a file without selecting it, without requiring hover", async () => {
		const user = userEvent.setup();
		render(<FileTabs />);
		const close = screen.getByRole("button", { name: "Close first.py" });
		close.focus();
		await user.keyboard(" ");
		expect(actions.closeTab).toHaveBeenCalledWith(0);
		expect(actions.setActiveTab).not.toHaveBeenCalled();
	});
});

describe("FileTabs — unsaved close", () => {
	it("keeps dirty tabs until discard is explicitly chosen", async () => {
		const user = userEvent.setup();
		render(<FileTabs />);
		await user.click(
			screen.getByRole("button", { name: "Close second.py" }),
		);
		expect(screen.getByRole("alertdialog")).toBeVisible();
		expect(screen.getByText("folder/second.py")).toBeVisible();
		expect(actions.closeTab).not.toHaveBeenCalled();
		await user.click(screen.getByRole("button", { name: "Keep editing" }));
		expect(actions.closeTab).not.toHaveBeenCalled();
		await user.click(
			screen.getByRole("button", { name: "Close second.py" }),
		);
		await user.click(
			screen.getByRole("button", { name: "Discard changes and close" }),
		);
		expect(actions.closeTab).toHaveBeenCalledWith(1);
	});
	it("confirms Close All and closes the selected indices in descending order", async () => {
		const user = userEvent.setup();
		render(<FileTabs />);
		await user.pointer({
			keys: "[MouseRight]",
			target: screen.getByRole("button", {
				name: "Open folder/first.py",
			}),
		});
		await user.click(screen.getByRole("menuitem", { name: "Close All" }));
		expect(actions.closeTab).not.toHaveBeenCalled();
		await user.click(
			screen.getByRole("button", { name: "Discard changes and close" }),
		);
		expect(actions.closeTab.mock.calls.map((call) => call[0])).toEqual([
			1, 0,
		]);
	});
});

describe("FileTabs — pending close identity", () => {
	it("resolves current file indices after a reorder and preserves newly opened tabs", async () => {
		const user = userEvent.setup();
		const initial = vi.mocked(useEditorSession)();
		const { rerender } = render(<FileTabs />);
		await user.pointer({
			keys: "[MouseRight]",
			target: screen.getByRole("button", {
				name: "Open folder/first.py",
			}),
		});
		await user.click(
			screen.getByRole("menuitem", { name: "Close Others" }),
		);
		const newlyOpened = {
			...initial.tabs[0],
			file: {
				...initial.tabs[0].file,
				name: "new.py",
				path: "folder/new.py",
			},
		};
		vi.mocked(useEditorSession).mockReturnValue({
			...initial,
			tabs: [initial.tabs[1], newlyOpened, initial.tabs[0]],
			activeTabIndex: 2,
		});
		rerender(<FileTabs />);
		await user.click(
			screen.getByRole("button", { name: "Discard changes and close" }),
		);
		expect(actions.closeTab.mock.calls.map((call) => call[0])).toEqual([0]);
	});
});

it("routes a missing file's conflict close through unsaved confirmation", async () => {
	const initial = vi.mocked(useEditorSession)();
	vi.mocked(useEditorSession).mockReturnValue({
		...initial,
		tabs: initial.tabs.map((tab, index) =>
			index === 1
				? {
						...tab,
						saveState: "conflict",
						conflictReason: "path_not_found",
					}
				: tab,
		),
	});
	const user = userEvent.setup();
	render(<FileTabs />);
	await user.click(
		screen.getByRole("button", { name: "Resolve conflict for second.py" }),
	);
	await user.click(screen.getByRole("menuitem", { name: /Close Tab/ }));
	expect(screen.getByRole("alertdialog")).toBeVisible();
	expect(actions.closeTab).not.toHaveBeenCalled();
	await user.click(screen.getByRole("button", { name: "Keep editing" }));
	expect(actions.closeTab).not.toHaveBeenCalled();
	await waitFor(() =>
		expect(
			screen.getByRole("button", {
				name: "Resolve conflict for second.py",
			}),
		).toHaveFocus(),
	);
});
